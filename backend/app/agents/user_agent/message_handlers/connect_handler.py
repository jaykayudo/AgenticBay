from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.user_agent.agent import MarketplaceUserAgent


class ConnectHandler:
    def __init__(self, agent: MarketplaceUserAgent) -> None:
        self.agent = agent

    async def handle(self, message: dict[str, Any]) -> None:
        data = message.get("data", {})
        capabilities: str = data.get("capabilities", "")
        agent_id: str = data.get("agent_id", "")

        context = (
            f"Successfully connected to service agent (id={agent_id}).\n"
            f"Capability document:\n{capabilities}\n\n"
            "Read the capability document carefully to determine the correct SERVICE_AGENT "
            "command name and argument structure, then send it."
        )

        await self.agent.memory.add_system_context(context)
        await self.agent.run_llm_turn()
