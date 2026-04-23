from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.security import verify_password
from app.models.api_keys import ApiKey
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

    async def revoke(self, key_id: uuid.UUID) -> ApiKey | None:
        return await self.update(key_id, is_active=False)

    async def validate_key(self, raw_key: str) -> ApiKey | None:
        """
        Locate a key by its plain-text prefix, then verify the bcrypt hash.
        Updates last_used_at on success.
        """
        prefix = raw_key[:8]
        result = await self.session.execute(
            select(ApiKey).where(
                ApiKey.key_prefix == prefix,
                ApiKey.is_active == True,  # noqa: E712
            )
        )
        candidates = list(result.scalars().all())
        for key in candidates:
            if verify_password(raw_key, key.key_hash):
                key.last_used_at = datetime.now(UTC)
                await self.session.flush()
                return key
        return None
