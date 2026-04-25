from __future__ import annotations

import json
from typing import Any

import voyageai
from loguru import logger

from app.core.database import asyncpg_connection


class VectorSearch:
    def __init__(self) -> None:
        self._vo: Any | None = None

    def _client(self) -> Any:
        if self._vo is None:
            self._vo = getattr(voyageai, "AsyncClient")()
        return self._vo

    # ──────────────────────────────────────────
    # PUBLIC: Main search method
    # ──────────────────────────────────────────
    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Embed the query and return similar agents ranked by cosine similarity."""
        try:
            embedding = await self._embed(query)
            return await self._search_pgvector(embedding, top_k, filters)
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    # ──────────────────────────────────────────
    # PUBLIC: Index a new agent when listed
    # ──────────────────────────────────────────
    async def index_agent(self, agent: dict[str, Any]) -> str | None:
        """Generate a document embedding and store it in the agent_embeddings table."""
        try:
            text_to_embed = f"{agent['name']}. {agent['description']}"
            embedding = await self._embed_document(text_to_embed)
            return await self._upsert_pgvector(
                agent_id=agent["id"],
                embedding=embedding,
                metadata={
                    "agent_id": agent["id"],
                    "name": agent["name"],
                    "description": agent["description"],
                    "category": agent.get("category", ""),
                    "tags": agent.get("tags", []),
                    "rating": agent.get("avg_rating", 0.0),
                    "pricing": agent.get("pricing_summary", {}),
                    "status": "ACTIVE",
                },
            )
        except Exception as e:
            logger.error(f"Failed to index agent {agent['id']}: {e}")
            return None

    # ──────────────────────────────────────────
    # PUBLIC: Remove agent from index
    # ──────────────────────────────────────────
    async def remove_agent(self, agent_id: str) -> bool:
        try:
            async with asyncpg_connection() as conn:
                await conn.execute(
                    "DELETE FROM agent_embeddings WHERE agent_id = $1",
                    agent_id,
                )
            return True
        except Exception as e:
            logger.error(f"Failed to remove agent {agent_id} from index: {e}")
            return False

    # ──────────────────────────────────────────
    # PRIVATE: Embeddings via Voyage AI
    # ──────────────────────────────────────────
    async def _embed(self, text: str) -> list[float]:
        """Embed a search query (input_type='query')."""
        result = await self._client().embed(texts=[text], model="voyage-3", input_type="query")
        return [float(x) for x in result.embeddings[0]]

    async def _embed_document(self, text: str) -> list[float]:
        """Embed a document for indexing (input_type='document')."""
        result = await self._client().embed(texts=[text], model="voyage-3", input_type="document")
        return [float(x) for x in result.embeddings[0]]

    # ──────────────────────────────────────────
    # PRIVATE: pgvector search
    # ──────────────────────────────────────────
    async def _search_pgvector(
        self,
        embedding: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        # $1 = embedding, $2 = top_k; extra filter params start at $3
        filter_clause = "WHERE ae.status = 'ACTIVE'"
        params: list[Any] = [str(embedding), top_k]
        param_idx = 3

        if filters:
            if filters.get("category"):
                filter_clause += f" AND ae.category = ${param_idx}"
                params.append(filters["category"])
                param_idx += 1
            if filters.get("min_rating") is not None:
                filter_clause += f" AND ae.rating >= ${param_idx}"
                params.append(filters["min_rating"])
                param_idx += 1

        sql = f"""
            SELECT
                ae.agent_id,
                ae.name,
                ae.description,
                ae.category,
                ae.tags,
                ae.rating,
                ae.pricing,
                1 - (ae.embedding <=> $1::vector) AS similarity_score
            FROM agent_embeddings ae
            {filter_clause}
            ORDER BY ae.embedding <=> $1::vector
            LIMIT $2
        """

        async with asyncpg_connection() as conn:
            rows = await conn.fetch(sql, *params)

        return [
            {
                "id": row["agent_id"],
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "tags": row["tags"],
                "rating": float(row["rating"]),
                # asyncpg returns jsonb as a string; parse it back to dict
                "pricing": json.loads(row["pricing"])
                if isinstance(row["pricing"], str)
                else row["pricing"],
                "similarity_score": float(row["similarity_score"]),
            }
            for row in rows
        ]

    # ──────────────────────────────────────────
    # PRIVATE: pgvector upsert
    # ──────────────────────────────────────────
    async def _upsert_pgvector(
        self,
        agent_id: str,
        embedding: list[float],
        metadata: dict[str, Any],
    ) -> str:
        async with asyncpg_connection() as conn:
            await conn.execute(
                """
                INSERT INTO agent_embeddings (
                    agent_id, name, description, category,
                    tags, rating, pricing, status, embedding
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9::vector)
                ON CONFLICT (agent_id) DO UPDATE SET
                    name        = EXCLUDED.name,
                    description = EXCLUDED.description,
                    category    = EXCLUDED.category,
                    tags        = EXCLUDED.tags,
                    rating      = EXCLUDED.rating,
                    pricing     = EXCLUDED.pricing,
                    status      = EXCLUDED.status,
                    embedding   = EXCLUDED.embedding,
                    updated_at  = NOW()
                """,
                agent_id,
                metadata["name"],
                metadata["description"],
                metadata["category"],
                metadata["tags"],
                metadata["rating"],
                json.dumps(metadata["pricing"]),
                metadata["status"],
                str(embedding),
            )
        return agent_id
