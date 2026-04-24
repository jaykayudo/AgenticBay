from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import aiohttp

from app.agents.orchestrator.llm import OrchestratorLLM
from app.agents.orchestrator.schema import (
    AgentSearchResult,
    CloseAppealResponse,
    CloseRequest,
    ConnectAgentRequest,
    ConnectResponse,
    ConnectResponseData,
    ErrorResponse,
    ErrorResponseData,
    # session
    JobSessionState,
    PaymentInfo,
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
from app.services.invoice_service import InvoiceService
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
        self.session_store = SessionStore()
        self.vector_search = VectorSearch()
        self.invoice_svc = InvoiceService()
        self.llm = OrchestratorLLM()
        self.http_timeout = aiohttp.ClientTimeout(total=30)

    # ──────────────────────────────────────────
    # ENTRY POINT: user agent messages
    # ──────────────────────────────────────────
    async def handle_message(
        self,
        session_id: str,
        raw_message: str,
        send: SendFn,
    ) -> None:
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

        handlers: dict[str, Any] = {
            "SEARCH_AGENT": self._handle_search,
            "CONNECT_AGENT": self._handle_connect,
            "SERVICE_AGENT": self._handle_service_request,
            "PAYMENT_SUCCESSFUL": self._handle_payment_successful,
            "CLOSE": self._handle_close,
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

        state.last_activity_at = datetime.now(UTC).isoformat()
        await self.session_store.save(state)
        await handler(state, message, send)

    # ──────────────────────────────────────────
    # ENTRY POINT: service agent messages
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
            enriched_query = await self.llm.enrich_search_query(message.data.message)
            raw_results = await self.vector_search.search(query=enriched_query, top_k=10)
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
            logger.error("Search failed: %s", e)
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

        state.connected_agent_id = agent_id
        state.agent_endpoint = agent.base_url
        state.agent_wallet_address = agent.wallet_address
        state.agent_capabilities = capabilities
        state.agent_orchestrator_key = agent.orchestrator_api_key
        state.phase = SessionPhase.ACTIVE

        # Create the Job record now that we know which agent is connected
        state.job_id = await self._create_job_in_db(state.session_id, state.user_id, agent_id)
        await self.session_store.save(state)

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
    # HANDLER: SERVICE_AGENT (forward to service)
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
        if isinstance(response, ServicePaymentRequest):
            await self._handle_payment_request(state, response, send)
        elif isinstance(response, ServiceJobDone):
            await self._handle_job_done(state, response, send)
        else:
            await send(ServiceAgentResponse(type="SERVICE_AGENT", data=response.data).to_text())

    # ──────────────────────────────────────────
    # PAYMENT REQUEST FLOW
    # ──────────────────────────────────────────
    async def _handle_payment_request(
        self, state: JobSessionState, response: ServicePaymentRequest, send: SendFn
    ) -> None:
        state.phase = SessionPhase.AWAITING_PAYMENT
        await self.session_store.save(state)

        if not state.job_id:
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="state_error",
                        message="No active job found for this session",
                    ),
                ).to_text()
            )
            return

        amount = float(response.data.amount)
        description = response.data.description
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

        try:
            invoice, escrow_wallet = await self.invoice_svc.create_invoice(
                session_id=state.session_id,
                job_id=state.job_id,
                payer_user_id=state.user_id,
                service_agent_id=state.connected_agent_id or "",
                amount=amount,
                description=description,
                payee_wallet_address=payee_address,
            )
        except Exception as exc:
            logger.error("Invoice creation failed session=%s: %s", state.session_id, exc)
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="invoice_error", message="Failed to create invoice"
                    ),
                ).to_text()
            )
            return

        state.pending_invoice_id = str(invoice.id)
        await self.session_store.save(state)

        from app.core.config import settings as _settings

        await send(
            PaymentResponse(
                type="PAYMENT",
                data=PaymentResponseData(
                    amount=amount,
                    description=description,
                    payment_info=PaymentInfo(
                        invoice_id=str(invoice.id),
                        invoice_wallet=escrow_wallet.wallet_address,
                        blockchain=_settings.BLOCKCHAIN,
                    ),
                ),
            ).to_text()
        )

    # ──────────────────────────────────────────
    # HANDLER: PAYMENT_SUCCESSFUL
    # ──────────────────────────────────────────
    async def _handle_payment_successful(
        self, state: JobSessionState, message: PaymentSuccessfulRequest, send: SendFn
    ) -> None:
        invoice_id = message.data.invoice_id

        confirmed = await self.invoice_svc.confirm_payment(invoice_id)
        if not confirmed:
            await send(
                ErrorResponse(
                    type="ERROR",
                    data=ErrorResponseData(
                        error_type="payment_error",
                        message=(
                            "Payment not yet received in escrow wallet. "
                            "Please wait a moment and try again."
                        ),
                    ),
                ).to_text()
            )
            return

        state.paid_invoice_ids.append(invoice_id)
        state.pending_invoice_id = None
        state.phase = SessionPhase.ACTIVE
        await self.session_store.save(state)

        await send(
            PaymentSuccessfulResponse(
                type="PAYMENT_SUCCESSFUL",
                data=PaymentSuccessfulResponseData(invoice_id=invoice_id),
            ).to_text()
        )

        # Notify service agent via LLM-resolved payment command
        capabilities = state.agent_capabilities or ""
        payment_command = await self.llm.find_payment_success_command(capabilities=capabilities)
        await self._send_to_service(
            state.session_id,
            ServiceAgentInvokeRequest(
                command=str(payment_command["command"]),
                arguments={
                    "invoice_id": invoice_id,
                },
            ),
        )

    # ──────────────────────────────────────────
    # JOB DONE
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
    # ──────────────────────────────────────────
    async def _handle_close(
        self, state: JobSessionState, message: CloseRequest, send: SendFn
    ) -> None:
        state.phase = SessionPhase.CLOSING
        await self.session_store.save(state)

        if state.paid_invoice_ids:
            results = await self.invoice_svc.disburse_session_invoices(session_id=state.session_id)
            logger.info("Disbursed %d invoices for session %s", len(results), state.session_id)

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

        state.phase = SessionPhase.CLOSED
        await self.session_store.save(state)
        await self._mark_job_completed(state)

    # ──────────────────────────────────────────
    # SEND TO SERVICE (WebSocket)
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
    # CONNECT HANDSHAKE (HTTP POST /connect)
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
                        "Service agent /connect returned %s  session=%s", resp.status, session_id
                    )
                    return False
        except Exception as exc:
            logger.error("_send_connect_request failed  session=%s: %s", session_id, exc)
            return False

    # ──────────────────────────────────────────
    # FETCH CAPABILITIES (HTTP GET /capabilities)
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
            logger.error("Failed to fetch capabilities from %s: %s", endpoint, e)
            return None

    # ──────────────────────────────────────────
    # DB HELPERS
    # ──────────────────────────────────────────
    async def _get_agent_from_db(self, agent_id: str) -> Agent | None:
        from app.core.database import AsyncSessionLocal
        from app.repositories.agent_repo import AgentRepository

        async with AsyncSessionLocal() as session:
            return await AgentRepository(session).get_by_id(uuid.UUID(agent_id))

    async def _create_job_in_db(self, session_id: str, user_id: str, agent_id: str) -> str:
        """Create a Job record and return its UUID string."""
        from app.core.database import AsyncSessionLocal
        from app.repositories.job_repo import JobRepository

        async with AsyncSessionLocal() as session:
            job = await JobRepository(session).create_job(
                session_id=uuid.UUID(session_id),
                buyer_id=uuid.UUID(user_id),
                agent_id=uuid.UUID(agent_id),
            )
            await session.commit()
            return str(job.id)

    async def _get_user_wallet_address(self, user_id: str) -> str:
        from app.core.database import AsyncSessionLocal
        from app.repositories.user_repo import UserRepository

        async with AsyncSessionLocal() as session:
            user = await UserRepository(session).get_by_id(uuid.UUID(user_id))
        if user is None or user.wallet_address is None:
            raise ValueError(f"No wallet address found for user {user_id}")
        return user.wallet_address

    async def _mark_job_completed(self, state: JobSessionState) -> None:
        if not state.job_id:
            return
        from app.core.database import AsyncSessionLocal
        from app.repositories.job_repo import JobRepository

        async with AsyncSessionLocal() as session:
            await JobRepository(session).mark_completed(uuid.UUID(state.job_id))
            await session.commit()
