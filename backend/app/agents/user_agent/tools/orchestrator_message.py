from __future__ import annotations

import logging
from typing import Any

from app.agents.user_agent.tools.base import Tool
from app.agents.user_agent.types import AgentState

logger = logging.getLogger(__name__)

_STATE_MAP: dict[str, AgentState] = {
    "SEARCH_AGENT": AgentState.SEARCHING,
    "CONNECT_AGENT": AgentState.CONNECTING,
    "PAYMENT_SUCCESSFUL": AgentState.ACTIVE,
    "CLOSE": AgentState.CLOSING,
}


class SendOrchestratorMessageTool(Tool):
    name = "send_orchestrator_message"
    description = (
        "Send a typed command to the marketplace orchestrator. "
        "Use SEARCH_AGENT to find service agents, CONNECT_AGENT to connect to one, "
        "SERVICE_AGENT to invoke a command on the connected agent, "
        "PAYMENT_SUCCESSFUL once the user has paid an invoice, "
        "and CLOSE to end the session and trigger disbursement. "
        "The orchestrator response will arrive asynchronously as [SYSTEM CONTEXT] on the next turn."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["message_type", "data"],
        "properties": {
            "message_type": {
                "type": "string",
                "enum": [
                    "SEARCH_AGENT",
                    "CONNECT_AGENT",
                    "SERVICE_AGENT",
                    "PAYMENT_SUCCESSFUL",
                    "CLOSE",
                ],
            },
            "data": {
                "type": "object",
                "description": "The data payload for the message type",
            },
        },
    }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        message_type: str = input["message_type"]
        data: dict[str, Any] = input["data"]
        payload = {"type": message_type, "data": data}

        await self.agent.orchestrator_ws.send(payload)
        logger.info("[%s] Sent %s to orchestrator", self.agent.session_id, message_type)

        if message_type in _STATE_MAP:
            self.agent.state = _STATE_MAP[message_type]

        return {
            "status": "sent",
            "message": f"{message_type} sent to orchestrator. Awaiting response.",
        }
