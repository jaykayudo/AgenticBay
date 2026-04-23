from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.users import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_wallet_address(self, address: str) -> User | None:
        result = await self.session.execute(select(User).where(User.wallet_address == address))
        return result.scalar_one_or_none()

    async def get_by_api_key(self, raw_key: str) -> User | None:
        from app.repositories.api_key_repo import ApiKeyRepository

        api_key = await ApiKeyRepository(self.session).validate_key(raw_key)
        if api_key is None:
            return None
        return await self.get_by_id(uuid.UUID(str(api_key.user_id)))
