from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.models.agents import Agent, AgentStatus
from app.repositories.base import BaseRepository


class AgentRepository(BaseRepository[Agent]):
    model = Agent

    async def get_by_slug(self, slug: str) -> Agent | None:
        result = await self.session.execute(select(Agent).where(Agent.slug == slug))
        return result.scalar_one_or_none()

    async def get_active_agents(self, *, limit: int = 100, offset: int = 0) -> list[Agent]:
        result = await self.session.execute(
            select(Agent).where(Agent.status == AgentStatus.ACTIVE).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_owner(self, owner_id: uuid.UUID) -> list[Agent]:
        result = await self.session.execute(select(Agent).where(Agent.owner_id == owner_id))
        return list(result.scalars().all())

    async def update_stats(
        self,
        agent_id: uuid.UUID,
        *,
        total_jobs: int | None = None,
        success_rate: Decimal | None = None,
        avg_rating: Decimal | None = None,
        total_earned: Decimal | None = None,
        avg_duration_sec: Decimal | None = None,
    ) -> Agent | None:
        kwargs: dict[str, Any] = {}
        if total_jobs is not None:
            kwargs["total_jobs"] = total_jobs
        if success_rate is not None:
            kwargs["success_rate"] = success_rate
        if avg_rating is not None:
            kwargs["avg_rating"] = avg_rating
        if total_earned is not None:
            kwargs["total_earned"] = total_earned
        if avg_duration_sec is not None:
            kwargs["avg_duration_sec"] = avg_duration_sec
        if not kwargs:
            return await self.get_by_id(agent_id)
        return await self.update(agent_id, **kwargs)
