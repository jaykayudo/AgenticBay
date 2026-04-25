from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.user_agent.agent import MarketplaceUserAgent


class CloseAppealHandler:
    def __init__(self, agent: MarketplaceUserAgent) -> None:
        self.agent = agent

    async def handle(self, message: dict[str, Any]) -> None:
        data = message.get("data", {})
        job_message: str = data.get("message", "")
        details: dict[str, Any] = data.get("details", {})

        context = (
            f"The service agent has completed the job.\n"
            f"Message: {job_message}\n"
            f"Details:\n{json.dumps(details, indent=2)}\n\n"
            "Review the result. If it satisfactorily fulfils the user's request, "
            "call close_session with the final_result set to a human-readable summary "
            "of the result. If the result is unsatisfactory, you may send another "
            "SERVICE_AGENT command to request corrections."
        )

        await self.agent.memory.add_system_context(context)
        await self.agent.run_llm_turn()
