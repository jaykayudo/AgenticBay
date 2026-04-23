from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.models.sessions import Session, SessionPhase
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    model = Session

    async def get_active_sessions(self, *, limit: int = 100) -> list[Session]:
        result = await self.session.execute(
            select(Session).where(Session.phase != SessionPhase.CLOSED).limit(limit)
        )
        return list(result.scalars().all())

    async def mark_closed(self, session_id: uuid.UUID) -> Session | None:
        return await self.update(
            session_id,
            phase=SessionPhase.CLOSED,
            closed_at=datetime.now(UTC),
        )

    async def get_by_user(self, user_id: uuid.UUID) -> list[Session]:
        result = await self.session.execute(select(Session).where(Session.user_id == user_id))
        return list(result.scalars().all())
