from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import aiohttp

from app.agents.orchestrator.invoice import InvoiceService
from app.agents.orchestrator.llm import OrchestratorLLM
from app.agents.orchestrator.schema import (
    AgentSearchResult,
    CloseAppealResponse,
    CloseRequest,
    ConnectAgentRequest,
    ConnectResponse,
    ConnectResponseData,
    ContractData,
    ErrorResponse,
    ErrorResponseData,
    # session
    JobSessionState,
    PaymentResponse,
    PaymentResponseData,
    PaymentSuccessfulRequest,
    PaymentSuccessfulResponse,
    PaymentSuccessfulResponseData,
    SearchAgentRequest,
    # outbound to user
    SearchAgentResponse,
    SearchAgentResponseData,
    # service agent
    ServiceAgentInvokeRequest,
    ServiceAgentRequest,
    ServiceAgentResponse,
    ServiceConnectRequest,
    ServiceGenericResponse,
    ServiceJobDone,
    ServicePaymentRequest,
    ServiceProgressUpdate,
    SessionPhase,
    parse_service_agent_response,
    # inbound from user
    parse_user_agent_message,
)
from app.agents.orchestrator.session_store import SessionStore
from app.agents.orchestrator.vector_search import VectorSearch
from app.websocket.manager import session_manager

if TYPE_CHECKING:
    from app.models.agents import Agent

logger = logging.getLogger(__name__)

# Async callable that pushes a text message to one WS side
SendFn = Callable[[str], Awaitable[None]]


class OrchestratorAgent:
    """
    Core orchestration agent.
    One instance per marketplace deployment.
    Handles all active WebSocket sessions concurrently.
    """

    def __init__(self) -> None:
        self.session_store = SessionStore()  # Redis-backed
        self.vector_search = VectorSearch()  # pgvector / Pinecone
        self.invoice_svc = InvoiceService()  # Web3 contract calls
        self.llm = OrchestratorLLM()  # Claude / GPT wrapper
        self.http_timeout = aiohttp.ClientTimeout(total=30)  # only for /capabilities + /connect

    # ──────────────────────────────────────────
    # ENTRY POINT: called by WebSocket handler
    # on every incoming message from user agent
    # ──────────────────────────────────────────
    async def handle_message(
        self,
        session_id: str,
        raw_message: str,
        send: SendFn,  # async fn to push message back to user agent
    ) -> None:
        """
        Main message router.
        Parses the incoming text message and dispatches
        to the appropriate handler.
        """
        # Load session state
        state = await self.session_store.get(session_id)
        if not state:
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="session_error", message="Session not found or expired"
                    ),
                ).to_text()
            )
            return

        # Parse message
        try:
            message = parse_user_agent_message(raw_message)
        except ValueError as e:
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(error_type="validation_error", message=str(e)),
                ).to_text()
            )
            return

        # Dispatch to handler
        handlers: dict[str, Any] = {
            "SEARCH_AGENT":       self._handle_search,
            "CONNECT_AGENT":      self._handle_connect,
            "SERVICE_AGENT":      self._handle_service_request,
            "PAYMENT_SUCCESSFUL": self._handle_payment_successful,
            "CLOSE":              self._handle_close,
        }

        handler = handlers.get(message.type)
        if not handler:
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="validation_error",
                        message=f"Unknown command type: {message.type}",
                    ),
                ).to_text()
            )
            return

        # Update last activity
        state.last_activity_at = datetime.now(UTC).isoformat()
        await self.session_store.save(state)

        # Run handler
        await handler(state, message, send)

    # ──────────────────────────────────────────
    # ENTRY POINT: called by the service WS handler
    # on every incoming message from the service agent
    # ──────────────────────────────────────────
    async def handle_service_message(self, session_id: str, raw: str) -> None:
        state = await self.session_store.get(session_id)
        if not state:
            logger.warning("handle_service_message: no state for session=%s", session_id)
            return

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Invalid JSON from service agent  session=%s", session_id)
            return

        parsed = parse_service_agent_response(data)

        # PROGRESS updates are forwarded directly to the user as-is
        if isinstance(parsed, ServiceProgressUpdate):
            await session_manager.send_to_user(
                session_id,
                ServiceAgentResponse(
                    type="SERVICE_AGENT",
                    message=parsed.data.message,
                    data={"progress": parsed.data.progress},
                ).to_text(),
            )
            return

        async def send_to_user(text: str) -> None:
            await session_manager.send_to_user(session_id, text)

        state.last_activity_at = datetime.now(UTC).isoformat()
        await self.session_store.save(state)
        await self._handle_service_response(state, parsed, send_to_user)

    # ──────────────────────────────────────────
    # HANDLER: SEARCH_AGENT
    # ──────────────────────────────────────────
    async def _handle_search(
        self, state: JobSessionState, message: SearchAgentRequest, send: SendFn
    ) -> None:

        state.phase = SessionPhase.SEARCHING
        await self.session_store.save(state)

        try:
            # LLM enriches the search query
            enriched_query = await self.llm.enrich_search_query(message.data.message)

            # Vector search over agent descriptions
            raw_results = await self.vector_search.search(query=enriched_query, top_k=10)

            # LLM reranks results
            reranked = await self.llm.rerank_agents(
                original_query=message.data.message, agents=raw_results
            )

            agents = [
                AgentSearchResult(
                    id=str(a["id"]),
                    name=str(a["name"]),
                    description=str(a["description"]),
                    rating=float(a["rating"]),
                    pricing=a["pricing"],
                )
                for a in reranked
            ]

            await send(
                SearchAgentResponse(
                    type="SEARCH_AGENT", data=SearchAgentResponseData(agents=agents)
                ).to_text()
            )

        except Exception as e:
            logger.error(f"Search failed: {e}")
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="search_error", message="Failed to search for agents"
                    ),
                ).to_text()
            )

    # ──────────────────────────────────────────
    # HANDLER: CONNECT_AGENT
    # ──────────────────────────────────────────
    async def _handle_connect(
        self, state: JobSessionState, message: ConnectAgentRequest, send: SendFn
    ) -> None:

        state.phase = SessionPhase.CONNECTING
        await self.session_store.save(state)

        agent_id = message.data.agent_id

        # Fetch agent from DB
        agent = await self._get_agent_from_db(agent_id)
        if not agent:
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="not_found_error", message=f"Agent {agent_id} not found"
                    ),
                ).to_text()
            )
            return

        # Fetch capability document from service agent
        capabilities = await self._fetch_capabilities(agent.base_url)
        if not capabilities:
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="connect_error", message="Failed to connect to service agent"
                    ),
                ).to_text()
            )
            return

        # Update session state
        state.connected_agent_id     = agent_id
        state.agent_endpoint         = agent.base_url
        state.agent_wallet_address   = agent.wallet_address
        state.agent_capabilities     = capabilities
        state.agent_orchestrator_key = agent.orchestrator_api_key
        state.phase                  = SessionPhase.ACTIVE
        await self.session_store.save(state)

        # Tell service agent to dial into our WS room
        connected = await self._send_connect_request(
            endpoint=agent.base_url,
            session_id=state.session_id,
            token=state.auth_token,
            orchestrator_key=agent.orchestrator_api_key,
        )
        if not connected:
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="connect_error",
                        message=(
                            "Service agent accepted capabilities request "
                            "but failed to open WS connection"
                        ),
                    ),
                ).to_text()
            )
            return

        await send(
            ConnectResponse(
                type="CONNECT",
                data=ConnectResponseData(agent_id=agent_id, capabilities=capabilities),
            ).to_text()
        )

    # ──────────────────────────────────────────
    # HANDLER: SERVICE_AGENT
    # The core infinite loop handler.
    # Forwards user command to service agent,
    # interprets response, acts accordingly.
    # ──────────────────────────────────────────
    async def _handle_service_request(
        self, state: JobSessionState, message: ServiceAgentRequest, send: SendFn
    ) -> None:

        if not state.connected_agent_id:
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="state_error",
                        message="No agent connected. Send CONNECT_AGENT first.",
                    ),
                ).to_text()
            )
            return

        if not session_manager.is_service_connected(state.session_id):
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="state_error",
                        message="Service agent WS not connected. Try reconnecting the agent.",
                    ),
                ).to_text()
            )
            return

        # Forward command to service agent over its WS room.
        # Response arrives asynchronously in handle_service_message.
        invoke_request = ServiceAgentInvokeRequest(
            command=message.data.command,
            arguments=message.data.arguments,
        )
        await self._send_to_service(state.session_id, invoke_request)

    # ──────────────────────────────────────────
    # SERVICE RESPONSE INTERPRETER
    # ──────────────────────────────────────────
    async def _handle_service_response(
        self,
        state: JobSessionState,
        response: ServicePaymentRequest | ServiceJobDone | ServiceGenericResponse,
        send: SendFn,
    ) -> None:

        # ── PAYMENT REQUEST ──
        if isinstance(response, ServicePaymentRequest):
            await self._handle_payment_request(state, response, send)

        # ── JOB DONE ──
        elif isinstance(response, ServiceJobDone):
            await self._handle_job_done(state, response, send)

        # ── GENERIC RESPONSE — forward to user agent ──
        else:
            await send(ServiceAgentResponse(type="SERVICE_AGENT", data=response.data).to_text())

    # ──────────────────────────────────────────
    # PAYMENT REQUEST FLOW
    # Service agent wants payment →
    # orchestrator creates invoice →
    # sends invoice details to user agent
    # ──────────────────────────────────────────
    async def _handle_payment_request(
        self, state: JobSessionState, response: ServicePaymentRequest, send: SendFn
    ) -> None:

        state.phase = SessionPhase.AWAITING_PAYMENT
        await self.session_store.save(state)

        amount = float(response.data.amount)
        description = response.data.description

        # Use agent's registered wallet if not specified
        payee_address = response.data.address or state.agent_wallet_address

        if not payee_address:
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="payment_error", message="No payment address available"
                    ),
                ).to_text()
            )
            return

        # Create escrow invoice via smart contract
        invoice = await self.invoice_svc.create_invoice(
            session_id=state.session_id,
            payer_address=await self._get_user_wallet_address(state.user_id),
            payee_address=payee_address,
            amount=amount,
            description=description,
        )

        if not invoice:
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="invoice_error", message="Failed to create invoice"
                    ),
                ).to_text()
            )
            return

        # Save pending invoice to state
        state.pending_invoice_id = invoice["invoice_id"]
        await self.session_store.save(state)

        # Send invoice details to user agent
        await send(
            PaymentResponse(
                type="PAYMENT",
                data=PaymentResponseData(
                    amount=amount,
                    description=description,
                    contract_data=ContractData(
                        invoice_id=invoice["invoice_id"],
                        invoice_contract=invoice["contract_address"],
                        function_name="payInvoice",
                    ),
                ),
            ).to_text()
        )

    # ──────────────────────────────────────────
    # HANDLER: PAYMENT_SUCCESSFUL
    # User agent confirms payment made →
    # orchestrator verifies on-chain →
    # notifies service agent to continue
    # ──────────────────────────────────────────
    async def _handle_payment_successful(
        self, state: JobSessionState, message: PaymentSuccessfulRequest, send: SendFn
    ) -> None:

        invoice_id = message.data.invoice_id

        # Verify payment on-chain
        is_paid = await self.invoice_svc.verify_payment(invoice_id)

        if not is_paid:
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="payment_error",
                        message="Payment has not been confirmed on-chain",
                    ),
                ).to_text()
            )
            return

        # Track paid invoice in session
        state.paid_invoice_ids.append(invoice_id)
        state.pending_invoice_id = None
        state.phase = SessionPhase.ACTIVE
        await self.session_store.save(state)

        # Confirm to user agent first
        await send(
            PaymentSuccessfulResponse(
                type="PAYMENT_SUCCESSFUL", data=PaymentSuccessfulResponseData(invoice_id=invoice_id)
            ).to_text()
        )

        # Use LLM to find the correct payment_confirmed command
        # from the capability document, then notify service agent over WS
        capabilities = state.agent_capabilities or ""
        payment_command = await self.llm.find_payment_success_command(
            capabilities=capabilities
        )

        await self._send_to_service(
            state.session_id,
            ServiceAgentInvokeRequest(
                command=str(payment_command["command"]),
                arguments={
                    "invoice_id": invoice_id,
                    "invoice_contract": self.invoice_svc.contract_address,
                },
            ),
        )

    # ──────────────────────────────────────────
    # JOB DONE HANDLER
    # Service agent signals completion →
    # orchestrator sends close appeal to user
    # ──────────────────────────────────────────
    async def _handle_job_done(
        self, state: JobSessionState, response: ServiceJobDone, send: SendFn
    ) -> None:

        state.phase = SessionPhase.CLOSING
        await self.session_store.save(state)

        await send(
            CloseAppealResponse(
                type="CLOSE_APPEAL",
                data={"message": response.data.message, "details": response.data.details},
            ).to_text()
        )

    # ──────────────────────────────────────────
    # HANDLER: CLOSE
    # User agent confirms session close →
    # disburse all paid invoices →
    # close session
    # ──────────────────────────────────────────
    async def _handle_close(
        self, state: JobSessionState, message: CloseRequest, send: SendFn
    ) -> None:

        state.phase = SessionPhase.CLOSING
        await self.session_store.save(state)

        # Disburse all paid invoices for this session via smart contract
        if state.paid_invoice_ids:
            await self.invoice_svc.disburse_session_invoices(session_id=state.session_id)

        # Notify service agent if still connected
        if state.paid_invoice_ids and session_manager.is_service_connected(state.session_id):
            await self._send_to_service(
                state.session_id,
                ServiceAgentInvokeRequest(
                    command="PAYMENT_TRANSFERRED",
                    arguments={
                        "session_id": state.session_id,
                        "invoice_ids": state.paid_invoice_ids,
                    },
                ),
            )

        # Mark session as closed
        state.phase = SessionPhase.CLOSED
        await self.session_store.save(state)

        # Persist to DB
        await self._mark_job_completed(state)

    # ──────────────────────────────────────────
    # SEND COMMAND TO SERVICE AGENT (WebSocket)
    # ──────────────────────────────────────────
    async def _send_to_service(
        self,
        session_id: str,
        message: ServiceAgentInvokeRequest,
    ) -> None:
        if not session_manager.is_service_connected(session_id):
            logger.warning("_send_to_service: no service WS for session=%s", session_id)
            return
        await session_manager.send_to_service(session_id, message.to_text())

    # ──────────────────────────────────────────
    # CONNECT HANDSHAKE TO SERVICE AGENT (HTTP)
    # POST /connect — tells the service how to
    # dial back into our WS service room.
    # ──────────────────────────────────────────
    async def _send_connect_request(
        self,
        endpoint: str,
        session_id: str,
        token: str,
        orchestrator_key: str,
    ) -> bool:
        from app.core.config import settings

        url = f"{endpoint.rstrip('/')}/connect"
        body = ServiceConnectRequest(
            session_id=session_id,
            token=token,
            orchestrator_ws_url=settings.ORCHESTRATOR_WS_URL,
            orchestrator_key=orchestrator_key,
        )

        try:
            async with aiohttp.ClientSession(timeout=self.http_timeout) as http:
                async with http.post(
                    url,
                    json=body.model_dump(),
                    headers={
                        "Content-Type": "application/json",
                        "X-Orchestrator-Key": orchestrator_key,
                    },
                ) as resp:
                    if resp.status == 200:
                        return True
                    logger.error(
                        "Service agent /connect returned %s  session=%s",
                        resp.status,
                        session_id,
                    )
                    return False
        except Exception as exc:
            logger.error("_send_connect_request failed  session=%s: %s", session_id, exc)
            return False

    # ──────────────────────────────────────────
    # FETCH CAPABILITIES
    # GET /capabilities
    # ──────────────────────────────────────────
    async def _fetch_capabilities(self, endpoint: str) -> str | None:
        url = f"{endpoint.rstrip('/')}/capabilities"

        try:
            async with aiohttp.ClientSession(timeout=self.http_timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data: dict[str, Any] = await resp.json()
                        msg = data.get("message")
                        return str(msg) if msg is not None else None
                    return None
        except Exception as e:
            logger.error(f"Failed to fetch capabilities from {endpoint}: {e}")
            return None

    # ──────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────
    async def _get_agent_from_db(self, agent_id: str) -> Agent | None:
        from app.core.database import AsyncSessionLocal
        from app.repositories.agent_repo import AgentRepository

        async with AsyncSessionLocal() as session:
            return await AgentRepository(session).get_by_id(uuid.UUID(agent_id))

    async def _get_user_wallet_address(self, user_id: str) -> str:
        from app.core.database import AsyncSessionLocal
        from app.repositories.user_repo import UserRepository

        async with AsyncSessionLocal() as session:
            user = await UserRepository(session).get_by_id(uuid.UUID(user_id))
        if user is None or user.wallet_address is None:
            raise ValueError(f"No wallet address found for user {user_id}")
        return user.wallet_address

    async def _mark_job_completed(self, state: JobSessionState) -> None:
        from app.core.database import AsyncSessionLocal
        from app.repositories.job_repo import JobRepository

        async with AsyncSessionLocal() as session:
            await JobRepository(session).mark_completed(uuid.UUID(state.session_id))
            await session.commit()
