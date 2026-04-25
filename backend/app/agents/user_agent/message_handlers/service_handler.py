from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.user_agent.agent import MarketplaceUserAgent


class ServiceHandler:
    def __init__(self, agent: MarketplaceUserAgent) -> None:
        self.agent = agent

    async def handle(self, message: dict[str, Any]) -> None:
        data = message.get("data")
        msg = message.get("message")

        if data:
            context = (
                f"The service agent returned data:\n{json.dumps(data, indent=2)}\n\n"
                "Interpret this data for the user and decide next steps."
            )
        elif msg:
            context = f"The service agent sent a message: {msg}"
        else:
            context = "The service agent responded with no data."

        await self.agent.memory.add_system_context(context)
        await self.agent.run_llm_turn()
