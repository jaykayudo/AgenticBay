from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.user_agent.agent import MarketplaceUserAgent


class SearchHandler:
    def __init__(self, agent: MarketplaceUserAgent) -> None:
        self.agent = agent

    async def handle(self, message: dict[str, Any]) -> None:
        agents: list[dict[str, Any]] = message.get("data", {}).get("agents", [])

        if not agents:
            context = "The orchestrator returned no matching service agents for this request."
        else:
            agent_list = "\n".join(
                f"- ID: {a['id']} | Name: {a['name']} | Rating: {a['rating']} "
                f"| Pricing: {json.dumps(a.get('pricing', {}))} | {a['description']}"
                for a in agents
            )
            context = (
                f"The orchestrator returned {len(agents)} service agent(s):\n{agent_list}\n\n"
                "Choose the most suitable agent based on description, rating, and pricing. "
                "Briefly explain your choice to the user via user_feedback, then send CONNECT_AGENT."
            )

        await self.agent.memory.add_system_context(context)
        await self.agent.run_llm_turn()
