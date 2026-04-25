from __future__ import annotations

from typing import Any

from app.agents.user_agent.tools.base import Tool
from app.agents.user_agent.types import AgentState


class UserPromptTool(Tool):
    name = "user_prompt"
    description = (
        "Ask the user a clarifying question via an interactive modal. "
        "Use this when the request is ambiguous or you need to choose between options. "
        "Supports input types: 'text' (free text), 'choice' (single select), "
        "'confirm' (yes/no), 'multi_choice' (multi select). "
        "The user's answer arrives as MODAL_RESPONSE on the next turn."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["question", "input_type"],
        "properties": {
            "question": {"type": "string"},
            "input_type": {
                "type": "string",
                "enum": ["text", "choice", "confirm", "multi_choice"],
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Required for choice and multi_choice types",
            },
        },
    }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        await self.agent.user_ws.send(
            {
                "type": "USER_PROMPT_MODAL",
                "data": {
                    "question": input["question"],
                    "input_type": input["input_type"],
                    "options": input.get("options"),
                    "requires_response": True,
                },
            }
        )
        self.agent.state = AgentState.AWAITING_USER
        return {
            "status": "awaiting_user",
            "message": "User prompt shown. Answer arrives next turn.",
        }
