from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.agents.user_agent.agent import MarketplaceUserAgent


class Tool(ABC):
    name: str
    description: str
    input_schema: dict[str, Any]

    def __init__(self, agent: MarketplaceUserAgent) -> None:
        self.agent = agent

    @abstractmethod
    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool and return a result dict."""

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
