from __future__ import annotations

from typing import Any

from app.agents.orchestrator.vector_search import VectorSearch


class AgentVectorIndexError(Exception):
    """Raised when an agent cannot be indexed for vector search."""


class VectorService:
    def __init__(self, vector_search: VectorSearch | None = None) -> None:
        self.vector_search = vector_search or VectorSearch()

    async def index_agent(self, payload: dict[str, Any]) -> str:
        embedding_id = await self.vector_search.index_agent(payload)
        if embedding_id is None:
            raise AgentVectorIndexError("Agent description could not be indexed.")
        return embedding_id

    async def remove_agent(self, agent_id: str) -> None:
        await self.vector_search.remove_agent(agent_id)
