from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.agents.user_agent.tools.base import Tool


class UserFeedbackTool(Tool):
    name = "user_feedback"
    description = (
        "Send a message to the user's chat interface. "
        "Use this for progress updates, explaining agent choices, sharing intermediate results, "
        "and delivering the final result before closing. "
        "type can be 'info', 'progress', 'success', 'warning', or 'result'."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["message"],
        "properties": {
            "message": {"type": "string"},
            "type": {
                "type": "string",
                "enum": ["info", "progress", "success", "warning", "result"],
                "default": "info",
            },
        },
    }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        await self.agent.user_ws.send(
            {
                "type": "AGENT_MESSAGE",
                "data": {
                    "message": input["message"],
                    "message_type": input.get("type", "info"),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        )
        return {"status": "delivered"}
