from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from app.core.security import verify_password
from app.models.api_keys import ApiKey, ApiKeyAuditLog
from app.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey]):
    model = ApiKey

    async def get_user_keys(
        self,
        user_id: uuid.UUID,
        *,
        active_only: bool = True,
    ) -> list[ApiKey]:
        q = select(ApiKey).where(ApiKey.user_id == user_id)
        if active_only:
            q = q.where(ApiKey.is_active == True)  # noqa: E712
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_user_key(self, key_id: uuid.UUID, user_id: uuid.UUID) -> ApiKey | None:
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_active_count(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.user_id == user_id,
                ApiKey.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one()

    async def get_created_today_count(self, user_id: uuid.UUID) -> int:
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.session.execute(
            select(func.count(ApiKey.id)).where(
                ApiKey.user_id == user_id,
                ApiKey.created_at >= today_start,
            )
        )
        return result.scalar_one()

    async def revoke(
        self,
        key_id: uuid.UUID,
        *,
        reason: str | None = None,
    ) -> ApiKey | None:
        now = datetime.now(UTC)
        return await self.update(
            key_id,
            is_active=False,
            revoked_at=now,
            revoked_reason=reason,
        )

    async def validate_key(self, raw_key: str) -> ApiKey | None:
        """
        Locate a key by its plain-text prefix and verify the bcrypt hash.
        Checks is_active and expiry. Callers should call track_usage() separately.
        """
        prefix = raw_key[:16]
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(ApiKey)
            .where(
                ApiKey.key_prefix == prefix,
                ApiKey.is_active == True,  # noqa: E712
            )
            .options(selectinload(ApiKey.user))
        )
        candidates = list(result.scalars().all())
        for key in candidates:
            if key.expires_at and key.expires_at.replace(tzinfo=UTC) < now:
                continue
            if verify_password(raw_key, key.key_hash):
                return key
        return None

    async def track_usage(
        self,
        key_id: uuid.UUID,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        await self.session.execute(
            update(ApiKey)
            .where(ApiKey.id == key_id)
            .values(
                last_used_at=now,
                last_used_ip=ip,
                last_used_user_agent=user_agent,
                usage_count=ApiKey.usage_count + 1,
            )
        )

    async def expire_stale_keys(self) -> int:
        """Mark all expired-but-still-active keys as inactive. Returns count updated."""
        now = datetime.now(UTC)
        result = await self.session.execute(
            update(ApiKey)
            .where(
                ApiKey.is_active == True,  # noqa: E712
                ApiKey.expires_at.is_not(None),
                ApiKey.expires_at <= now,
            )
            .values(is_active=False, revoked_at=now, revoked_reason="expired")
            .returning(ApiKey.id)
        )
        rows = result.fetchall()
        return len(rows)

    # ── Audit log methods ─────────────────────────────────────────────────────

    async def add_audit_log(
        self,
        user_id: uuid.UUID,
        key_id: uuid.UUID | None,
        action: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ApiKeyAuditLog:
        log = ApiKeyAuditLog(
            user_id=user_id,
            key_id=key_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=metadata or {},
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_audit_logs(
        self,
        key_id: uuid.UUID,
        *,
        limit: int = 100,
    ) -> list[ApiKeyAuditLog]:
        result = await self.session.execute(
            select(ApiKeyAuditLog)
            .where(ApiKeyAuditLog.key_id == key_id)
            .order_by(ApiKeyAuditLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_old_audit_logs(self, older_than_days: int = 365) -> int:
        cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
        result = await self.session.execute(
            select(ApiKeyAuditLog).where(ApiKeyAuditLog.created_at < cutoff)
        )
        logs = list(result.scalars().all())
        for log in logs:
            await self.session.delete(log)
        await self.session.flush()
        return len(logs)
