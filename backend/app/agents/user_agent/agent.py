from __future__ import annotations

import logging
from typing import Any

from app.agents.user_agent.llm import AgentLLM
from app.agents.user_agent.memory import SessionMemory
from app.agents.user_agent.message_handlers.dispatcher import OrchestratorMessageDispatcher
from app.agents.user_agent.system_prompt import SYSTEM_PROMPT
from app.agents.user_agent.tools.api_request import ApiRequestTool
from app.agents.user_agent.tools.close_session import CloseSessionTool
from app.agents.user_agent.tools.orchestrator_message import SendOrchestratorMessageTool
from app.agents.user_agent.tools.payment_confirm import RequestPaymentConfirmationTool
from app.agents.user_agent.tools.user_feedback import UserFeedbackTool
from app.agents.user_agent.tools.user_prompt import UserPromptTool
from app.agents.user_agent.types import AgentState, AutoPaySettings
from app.agents.user_agent.ws_clients.orchestrator_client import OrchestratorWSClient
from app.agents.user_agent.ws_clients.user_client import UserWSClient

logger = logging.getLogger(__name__)


class MarketplaceUserAgent:
    """
    LLM-powered marketplace user agent.
    One instance per active chat session.
    """

    def __init__(self, session_id: str, user_id: str) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.memory = SessionMemory(session_id)
        self.llm = AgentLLM()
        self.state = AgentState.IDLE
        self.job_session_id: str | None = None

        # Set during start()
        self.user_ws: UserWSClient = None  # type: ignore[assignment]
        self.orchestrator_ws: OrchestratorWSClient = None  # type: ignore[assignment]

        self.tools = self._build_tools()
        self._dispatcher = OrchestratorMessageDispatcher(self)

    # ──────────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────────

    async def start(self, user_ws: UserWSClient, initial_user_message: str) -> None:
        """Called when the user initiates a chat session."""
        self.user_ws = user_ws
        self.orchestrator_ws = OrchestratorWSClient(self)
        await self.orchestrator_ws.start_and_connect()
        await self.memory.add_user_message(initial_user_message)
        await self.run_llm_turn()

    async def handle_user_message(self, message: str) -> None:
        """User typed a new message mid-session."""
        await self.memory.add_user_message(message)
        await self.run_llm_turn()

    async def handle_orchestrator_message(self, message: dict[str, Any]) -> None:
        """Routes incoming orchestrator WS messages to handlers."""
        logger.debug("[%s] Orchestrator message: %s", self.session_id, message.get("type"))
        await self._dispatcher.dispatch(message)

    async def handle_user_response(self, response: dict[str, Any]) -> None:
        """User responded to a modal (payment confirmation, clarification prompt)."""
        response_type = response.get("type", "MODAL_RESPONSE")
        await self.memory.add_user_message(
            f"[USER RESPONSE to modal] {response_type}: {response.get('value', response)}"
        )
        self.state = AgentState.ACTIVE
        await self.run_llm_turn()

    async def close(self, final_result: str) -> None:
        """Clean up resources and mark session as CLOSED."""
        self.state = AgentState.CLOSED
        await self.memory.clear()
        if self.orchestrator_ws:
            await self.orchestrator_ws.close()
        logger.info("[%s] Agent closed. Result: %s", self.session_id, final_result[:80])

    # ──────────────────────────────────────────────────────────────────────────
    # CORE LLM LOOP
    # ──────────────────────────────────────────────────────────────────────────

    async def run_llm_turn(self, prompt_context: str | None = None) -> None:
        """
        Tool-calling loop:
        1. Call LLM with full memory + tools
        2. If tool_use: execute tools, add results, loop
        3. If text: send to user via user_feedback, end turn
        4. If close_session called: exit immediately
        """
        if prompt_context:
            await self.memory.add_system_context(prompt_context)

        while True:
            messages = await self.memory.get_messages_for_llm()

            try:
                response = await self.llm.call_with_tools(
                    messages=messages,
                    tools=[t.schema() for t in self.tools.values()],
                    system=SYSTEM_PROMPT,
                )
            except Exception:
                logger.exception("[%s] LLM call failed", self.session_id)
                await self.user_ws.send(
                    {
                        "type": "AGENT_MESSAGE",
                        "data": {
                            "message": "I encountered an error. Please try again.",
                            "message_type": "warning",
                        },
                    }
                )
                break

            # Serialize content for memory storage (Anthropic blocks → dicts)
            content_dicts = [
                b.model_dump() if hasattr(b, "model_dump") else b for b in response.content
            ]
            await self.memory.add_assistant_message(content_dicts)

            if response.stop_reason == "tool_use":
                tool_calls = [b for b in response.content if b.type == "tool_use"]
                closed = False
                awaiting_external = False

                for tool_call in tool_calls:
                    tool = self.tools.get(tool_call.name)
                    if tool is None:
                        result: dict[str, Any] = {"error": f"Unknown tool: {tool_call.name}"}
                    else:
                        try:
                            result = await tool.execute(tool_call.input)
                        except Exception as exc:
                            logger.exception("[%s] Tool %s failed", self.session_id, tool_call.name)
                            result = {"error": str(exc)}

                    await self.memory.add_tool_result(tool_call.id, result)

                    if tool_call.name == "close_session":
                        closed = True
                    # After these tools the agent must wait for an external response
                    # (orchestrator message or user modal), so the loop ends here.
                    elif tool_call.name in (
                        "send_orchestrator_message",
                        "request_payment_confirmation",
                        "user_prompt",
                    ):
                        awaiting_external = True

                if closed or awaiting_external:
                    return

                continue  # give LLM the tool results

            # Text / end_turn response — forward to user
            text = "".join(getattr(b, "text", "") for b in response.content if hasattr(b, "text"))
            if text:
                await self.tools["user_feedback"].execute({"message": text, "type": "info"})

            break

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    async def _get_auto_pay_settings(self) -> AutoPaySettings:
        """Load the user's auto-pay settings from the database."""
        try:
            import uuid

            from app.core.database import AsyncSessionLocal
            from app.repositories.user_repo import UserRepository

            async with AsyncSessionLocal() as db:
                repo = UserRepository(db)
                user = await repo.get_by_id(uuid.UUID(self.user_id))

            if user is None:
                return AutoPaySettings(
                    auto_pay_enabled=False,
                    auto_pay_max_per_job=0,
                    auto_pay_max_per_day=0,
                )
            return AutoPaySettings(
                auto_pay_enabled=getattr(user, "auto_pay_enabled", False),
                auto_pay_max_per_job=float(getattr(user, "auto_pay_max_per_job", 0) or 0),
                auto_pay_max_per_day=float(getattr(user, "auto_pay_max_per_day", 0) or 0),
            )
        except Exception:
            logger.exception("[%s] Failed to load auto-pay settings", self.session_id)
            return AutoPaySettings(
                auto_pay_enabled=False,
                auto_pay_max_per_job=0,
                auto_pay_max_per_day=0,
            )

    def _build_tools(self) -> dict[str, Any]:
        return {
            "send_orchestrator_message": SendOrchestratorMessageTool(self),
            "user_feedback": UserFeedbackTool(self),
            "request_payment_confirmation": RequestPaymentConfirmationTool(self),
            "user_prompt": UserPromptTool(self),
            "api_request": ApiRequestTool(self),
            "close_session": CloseSessionTool(self),
        }
