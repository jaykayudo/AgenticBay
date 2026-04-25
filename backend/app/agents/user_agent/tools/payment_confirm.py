from __future__ import annotations

from typing import Any

from app.agents.user_agent.tools.base import Tool
from app.agents.user_agent.types import AgentState


class RequestPaymentConfirmationTool(Tool):
    name = "request_payment_confirmation"
    description = (
        "Show a payment confirmation modal to the user and await their response. "
        "Use this when the orchestrator sends a PAYMENT message and auto_pay is not enabled "
        "or the amount exceeds the user's auto_pay limits. "
        "The user's response (confirmed or declined) will arrive as a MODAL_RESPONSE on the next turn."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["invoice_id", "amount", "description", "escrow_wallet"],
        "properties": {
            "invoice_id": {"type": "string"},
            "amount": {"type": "number"},
            "description": {"type": "string"},
            "escrow_wallet": {"type": "string"},
        },
    }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        await self.agent.user_ws.send(
            {
                "type": "PAYMENT_CONFIRMATION_MODAL",
                "data": {
                    "invoice_id": input["invoice_id"],
                    "amount": input["amount"],
                    "currency": "USDC",
                    "description": input["description"],
                    "escrow_wallet": input["escrow_wallet"],
                    "requires_response": True,
                },
            }
        )
        self.agent.state = AgentState.AWAITING_USER
        return {
            "status": "awaiting_user",
            "message": "Payment confirmation modal shown. User response arrives next turn.",
        }
