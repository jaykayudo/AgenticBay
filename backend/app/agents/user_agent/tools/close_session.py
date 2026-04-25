from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.agents.user_agent.tools.base import Tool

logger = logging.getLogger(__name__)


class CloseSessionTool(Tool):
    name = "close_session"
    description = (
        "End the current job session and deliver the final result to the user. "
        "Call this when the job is complete or when an unrecoverable error occurred. "
        "This sends CLOSE to the orchestrator (triggers disbursement), delivers the "
        "final result to the user, and marks the session as CLOSED. "
        "Only call this when you are certain the session should end."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["final_result", "success"],
        "properties": {
            "final_result": {
                "type": "string",
                "description": "The final result or message for the user",
            },
            "success": {
                "type": "boolean",
                "description": "Whether the job completed successfully",
            },
            "summary": {
                "type": "string",
                "description": "Brief summary of what was accomplished",
            },
        },
    }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        # Send CLOSE to orchestrator (triggers disbursement)
        if self.agent.orchestrator_ws is not None:
            await self.agent.orchestrator_ws.send({"type": "CLOSE", "data": {}})

        # Deliver final result to user
        await self.agent.user_ws.send(
            {
                "type": "SESSION_COMPLETE",
                "data": {
                    "final_result": input["final_result"],
                    "success": input["success"],
                    "summary": input.get("summary", ""),
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            }
        )

        # Cleanup agent resources
        await self.agent.close(input["final_result"])

        logger.info("[%s] Session closed (success=%s)", self.agent.session_id, input["success"])
        return {"status": "closed"}
