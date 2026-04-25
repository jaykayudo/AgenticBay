from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.orchestrator.vector_search import VectorSearch
from app.models.agents import Agent, AgentAction, AgentStatus
from app.models.invoices import Invoice, InvoiceStatus
from app.models.jobs import Job
from app.models.reviews import Review, ReviewStatus

MarketplaceSort = Literal["relevance", "rating", "price_asc", "price_desc", "jobs"]

CACHE_TTL_SECONDS = 300


class MarketplaceSearchError(Exception):
    """Raised when marketplace search cannot be completed."""


@dataclass(frozen=True)
class PaginationMeta:
    total: int
    page: int
    page_size: int
    has_next: bool


@dataclass(frozen=True)
class MarketplaceListResult:
    agents: list[Agent]
    meta: PaginationMeta


@dataclass(frozen=True)
class MarketplaceSearchHit:
    agent: Agent
    relevance_score: float
    match_reason: str


@dataclass(frozen=True)
class MarketplaceSearchResult:
    query: str
    enriched_query: str
    orchestrator_suggestion: str
    results: list[MarketplaceSearchHit]


class TTLCache:
    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._values: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        cached = self._values.get(key)
        if cached is None:
            return None
        expires_at, value = cached
        if expires_at <= time.monotonic():
            self._values.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> Any:
        self._values[key] = (time.monotonic() + self.ttl_seconds, value)
        return value


marketplace_cache = TTLCache()


def speed_limit_seconds(speed: str | None) -> int | None:
    limits = {
        "instant": 15 * 60,
        "under_1_hour": 60 * 60,
        "same_day": 24 * 60 * 60,
        "one_to_three_days": 3 * 24 * 60 * 60,
        "three_to_seven_days": 7 * 24 * 60 * 60,
    }
    return limits.get(speed or "")


class SearchService:
    def __init__(self, db: AsyncSession, *, vector_search: VectorSearch | None = None) -> None:
        self.db = db
        self.vector_search = vector_search or VectorSearch()

    async def list_agents(
        self,
        *,
        category: str | None,
        min_rating: float | None,
        max_price: Decimal | None,
        speed: str | None,
        sort: MarketplaceSort,
        page: int,
        page_size: int,
        q: str | None,
    ) -> MarketplaceListResult:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        stmt = self._base_active_agent_query()
        stmt = self._apply_filters(
            stmt,
            category=category,
            min_rating=min_rating,
            max_price=max_price,
            speed=speed,
            q=q,
        )

        total = await self._count(stmt)
        stmt = self._apply_sort(stmt, sort=sort, q=q)
        result = await self.db.execute(
            stmt.offset((page - 1) * page_size)
            .limit(page_size)
            .options(selectinload(Agent.actions))
        )
        agents = list(result.scalars().unique().all())

        return MarketplaceListResult(
            agents=agents,
            meta=PaginationMeta(
                total=total,
                page=page,
                page_size=page_size,
                has_next=page * page_size < total,
            ),
        )

    async def get_agent_detail(self, agent_id: uuid.UUID) -> Agent | None:
        result = await self.db.execute(
            select(Agent)
            .where(Agent.id == agent_id, Agent.status == AgentStatus.ACTIVE)
            .options(selectinload(Agent.actions))
        )
        return result.scalar_one_or_none()

    async def get_reviews(self, agent_id: uuid.UUID, *, limit: int = 10) -> list[Review]:
        result = await self.db.execute(
            select(Review)
            .where(Review.agent_id == agent_id, Review.status == ReviewStatus.PUBLISHED)
            .order_by(Review.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search(self, *, query: str, limit: int = 10) -> MarketplaceSearchResult:
        normalized_query = query.strip()
        if not normalized_query:
            raise MarketplaceSearchError("Search query is required.")

        enriched_query = await self.enrich_query(normalized_query)
        raw_hits = await self.vector_search.search(query=enriched_query, top_k=limit)
        hits_by_id = {
            str(hit.get("id")): float(hit.get("similarity_score") or hit.get("score") or 0)
            for hit in raw_hits
            if hit.get("id")
        }

        agents = await self._agents_by_ranked_ids(list(hits_by_id.keys()))
        if not agents:
            agents = await self._keyword_fallback(normalized_query, limit)
            hits_by_id = {
                str(agent.id): max(0.3, 0.72 - (index * 0.04)) for index, agent in enumerate(agents)
            }

        ranked_hits = [
            MarketplaceSearchHit(
                agent=agent,
                relevance_score=round(hits_by_id.get(str(agent.id), 0), 4),
                match_reason=self.build_match_reason(agent, normalized_query),
            )
            for agent in agents[:limit]
        ]

        return MarketplaceSearchResult(
            query=normalized_query,
            enriched_query=enriched_query,
            orchestrator_suggestion=self.build_orchestrator_suggestion(
                ranked_hits, normalized_query
            ),
            results=ranked_hits,
        )

    async def categories(self) -> list[dict[str, Any]]:
        cached = marketplace_cache.get("categories")
        if cached is not None:
            return list(cached)

        result = await self.db.execute(
            select(Agent.categories).where(Agent.status == AgentStatus.ACTIVE)
        )
        counts: dict[str, int] = {}
        for categories in result.scalars().all():
            for category in categories or []:
                counts[str(category)] = counts.get(str(category), 0) + 1

        categories_payload = [
            {"category": category, "agentCount": count}
            for category, count in sorted(counts.items(), key=lambda item: item[0])
        ]
        return list(marketplace_cache.set("categories", categories_payload))

    async def featured(self, *, limit: int = 6) -> list[Agent]:
        cache_key = f"featured:{limit}"
        cached = marketplace_cache.get(cache_key)
        if cached is not None:
            return list(cached)

        result = await self.db.execute(
            select(Agent)
            .where(Agent.status == AgentStatus.ACTIVE)
            .order_by(Agent.avg_rating.desc(), Agent.total_jobs.desc(), Agent.created_at.desc())
            .limit(limit)
            .options(selectinload(Agent.actions))
        )
        agents = list(result.scalars().unique().all())
        return list(marketplace_cache.set(cache_key, agents))

    async def stats(self) -> dict[str, Any]:
        cached = marketplace_cache.get("stats")
        if cached is not None:
            return dict(cached)

        total_agents = await self.db.scalar(
            select(func.count()).select_from(Agent).where(Agent.status == AgentStatus.ACTIVE)
        )
        total_jobs = await self.db.scalar(select(func.count()).select_from(Job))
        total_volume = await self.db.scalar(
            select(func.coalesce(func.sum(Invoice.amount), 0)).where(
                Invoice.status.in_(
                    [
                        InvoiceStatus.PENDING_RELEASE,
                        InvoiceStatus.DISBURSING,
                        InvoiceStatus.DISBURSED,
                    ]
                )
            )
        )

        payload = {
            "totalAgents": int(total_agents or 0),
            "totalVolume": float(total_volume or 0),
            "totalJobs": int(total_jobs or 0),
        }
        return dict(marketplace_cache.set("stats", payload))

    async def enrich_query(self, query: str) -> str:
        # Deterministic enrichment placeholder for the LLM step. The return shape is stable for
        # embedding, while a production LLM client can replace this method directly.
        return (
            f"{query}. Match marketplace service agents by capabilities, category, expected "
            "deliverable, price, quality, and execution speed."
        )

    def build_match_reason(self, agent: Agent, query: str) -> str:
        categories = (
            ", ".join(str(category) for category in agent.categories[:2]) or "general service"
        )
        tags = ", ".join(str(tag) for tag in agent.tags[:2])
        tag_phrase = f" with strengths in {tags}" if tags else ""
        return (
            f"{agent.name} matches '{query}' through {categories}{tag_phrase}, "
            f"{float(agent.avg_rating):.1f} average rating, and {agent.total_jobs} completed jobs."
        )

    def build_orchestrator_suggestion(self, hits: list[MarketplaceSearchHit], query: str) -> str:
        if not hits:
            return f"No active agents strongly matched '{query}'. Try adding category or output details."

        top = hits[0]
        return (
            f"{top.agent.name} is the best fit for '{query}' because it has the strongest semantic "
            f"match, {float(top.agent.avg_rating):.1f} average rating, and a relevant service profile."
        )

    def _base_active_agent_query(self) -> Select[tuple[Agent]]:
        return select(Agent).where(Agent.status == AgentStatus.ACTIVE)

    def _apply_filters(
        self,
        stmt: Select[tuple[Agent]],
        *,
        category: str | None,
        min_rating: float | None,
        max_price: Decimal | None,
        speed: str | None,
        q: str | None,
    ) -> Select[tuple[Agent]]:
        if category:
            stmt = stmt.where(Agent.categories.contains([category]))
        if min_rating is not None:
            stmt = stmt.where(Agent.avg_rating >= Decimal(str(min_rating)))
        if max_price is not None:
            stmt = stmt.where(
                Agent.actions.any(
                    and_(AgentAction.is_active.is_(True), AgentAction.price <= max_price)
                )
            )
        speed_seconds = speed_limit_seconds(speed)
        if speed_seconds is not None:
            stmt = stmt.where(
                or_(Agent.avg_duration_sec.is_(None), Agent.avg_duration_sec <= speed_seconds)
            )
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(or_(Agent.name.ilike(pattern), Agent.description.ilike(pattern)))
        return stmt

    def _apply_sort(
        self,
        stmt: Select[tuple[Agent]],
        *,
        sort: MarketplaceSort,
        q: str | None,
    ) -> Select[tuple[Agent]]:
        min_price = (
            select(func.min(AgentAction.price))
            .where(AgentAction.agent_id == Agent.id, AgentAction.is_active.is_(True))
            .correlate(Agent)
            .scalar_subquery()
        )
        if sort == "rating":
            return stmt.order_by(Agent.avg_rating.desc(), Agent.total_jobs.desc())
        if sort == "price_asc":
            return stmt.order_by(min_price.asc().nulls_last(), Agent.avg_rating.desc())
        if sort == "price_desc":
            return stmt.order_by(min_price.desc().nulls_last(), Agent.avg_rating.desc())
        if sort == "jobs":
            return stmt.order_by(Agent.total_jobs.desc(), Agent.avg_rating.desc())
        if q:
            return stmt.order_by(
                func.length(Agent.name).asc(),
                Agent.avg_rating.desc(),
                Agent.total_jobs.desc(),
            )
        return stmt.order_by(
            Agent.avg_rating.desc(), Agent.total_jobs.desc(), Agent.created_at.desc()
        )

    async def _count(self, stmt: Select[tuple[Agent]]) -> int:
        subquery = stmt.with_only_columns(Agent.id).order_by(None).subquery()
        total = await self.db.scalar(select(func.count()).select_from(subquery))
        return int(total or 0)

    async def _agents_by_ranked_ids(self, agent_ids: list[str]) -> list[Agent]:
        parsed_ids: list[uuid.UUID] = []
        for agent_id in agent_ids:
            try:
                parsed_ids.append(uuid.UUID(agent_id))
            except ValueError:
                continue
        if not parsed_ids:
            return []

        result = await self.db.execute(
            select(Agent)
            .where(Agent.id.in_(parsed_ids), Agent.status == AgentStatus.ACTIVE)
            .options(selectinload(Agent.actions))
        )
        agents_by_id = {agent.id: agent for agent in result.scalars().unique().all()}
        return [agents_by_id[agent_id] for agent_id in parsed_ids if agent_id in agents_by_id]

    async def _keyword_fallback(self, query: str, limit: int) -> list[Agent]:
        pattern = f"%{query}%"
        result = await self.db.execute(
            select(Agent)
            .where(
                Agent.status == AgentStatus.ACTIVE,
                or_(Agent.name.ilike(pattern), Agent.description.ilike(pattern)),
            )
            .order_by(Agent.avg_rating.desc(), Agent.total_jobs.desc())
            .limit(limit)
            .options(selectinload(Agent.actions))
        )
        return list(result.scalars().unique().all())
