from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.models.jobs import Job, JobStatus
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    model = Job

    async def create_job(
        self,
        session_id: uuid.UUID,
        buyer_id: uuid.UUID,
        agent_id: uuid.UUID,
        *,
        action_id: uuid.UUID | None = None,
        raw_user_request: str | None = None,
    ) -> Job:
        return await self.create(
            session_id=session_id,
            buyer_id=buyer_id,
            agent_id=agent_id,
            action_id=action_id,
            raw_user_request=raw_user_request,
            status=JobStatus.AWAITING_INVOICE,
            started_at=datetime.now(UTC),
        )

    async def mark_completed(self, job_id: uuid.UUID) -> Job | None:
        return await self.update(
            job_id,
            status=JobStatus.COMPLETED,
            completed_at=datetime.now(UTC),
        )

    async def get_by_session(self, session_id: uuid.UUID) -> list[Job]:
        result = await self.session.execute(select(Job).where(Job.session_id == session_id))
        return list(result.scalars().all())

    async def get_by_buyer(self, buyer_id: uuid.UUID) -> list[Job]:
        result = await self.session.execute(select(Job).where(Job.buyer_id == buyer_id))
        return list(result.scalars().all())
