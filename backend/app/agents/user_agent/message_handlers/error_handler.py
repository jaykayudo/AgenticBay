from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.user_agent.agent import MarketplaceUserAgent


class ErrorHandler:
    def __init__(self, agent: MarketplaceUserAgent) -> None:
        self.agent = agent

    async def handle(self, message: dict[str, Any]) -> None:
        data = message.get("data", {})
        error_type: str = data.get("error_type", "unknown_error")
        error_msg: str = data.get("message", "An unknown error occurred")

        context = (
            f"The orchestrator returned an error:\n"
            f"  Type: {error_type}\n"
            f"  Message: {error_msg}\n\n"
            "Decide whether to retry the failed operation, try a different approach, "
            "or close the session. Explain the situation to the user via user_feedback."
        )

        await self.agent.memory.add_system_context(context)
        await self.agent.run_llm_turn()
