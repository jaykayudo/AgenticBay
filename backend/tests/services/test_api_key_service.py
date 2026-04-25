from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.api_keys import ApiKeyAuditAction, ApiKeyEnvironment, ApiKeyPermission
from app.repositories.api_key_repo import ApiKeyRepository
from app.services import api_key_service as service_module
from app.services.api_key_service import MAX_ACTIVE_KEYS, ApiKeyLimitError, ApiKeyService
from tests.conftest import make_user


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.counts: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        del ex
        self.values[key] = value

    async def delete(self, key: str) -> None:
        self.values.pop(key, None)

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        del key, seconds


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> FakeRedis:
    redis = FakeRedis()

    async def get_fake_redis() -> FakeRedis:
        return redis

    monkeypatch.setattr(service_module, "get_redis", get_fake_redis)
    return redis


async def test_generate_key_returns_raw_key_once_and_stores_hash(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session)

    created = await ApiKeyService(db_session).generate_key(
        user.id,
        name="Production Backend",
        environment=ApiKeyEnvironment.PRODUCTION,
        permissions=[ApiKeyPermission.SEARCH, ApiKeyPermission.HIRE],
        expires_in_days=30,
    )

    assert created.raw_key.startswith("mk_live_")
    assert len(created.raw_key) >= 50
    assert created.api_key.key_prefix == created.raw_key[:16]
    assert created.api_key.key_hash != created.raw_key
    assert verify_password(created.raw_key, created.api_key.key_hash)
    assert created.api_key.permissions == ["search", "hire"]
    assert created.api_key.expires_at is not None

    logs = await ApiKeyRepository(db_session).get_audit_logs(created.api_key.id)
    assert len(logs) == 1
    assert logs[0].action == ApiKeyAuditAction.CREATED


async def test_validate_and_get_user_uses_cache(
    db_session: AsyncSession,
    fake_redis: FakeRedis,
) -> None:
    user = await make_user(db_session)
    created = await ApiKeyService(db_session).generate_key(
        user.id,
        name="Sandbox",
        environment=ApiKeyEnvironment.SANDBOX,
    )

    user_id, key_id = await ApiKeyService(db_session).validate_and_get_user(created.raw_key)

    assert user_id == str(user.id)
    assert key_id == created.api_key.id
    assert fake_redis.values[f"apikey_cache:{created.api_key.key_prefix}"] == (
        f"{user.id}:{created.api_key.id}"
    )


async def test_revoke_invalidates_key_and_cache(
    db_session: AsyncSession,
    fake_redis: FakeRedis,
) -> None:
    user = await make_user(db_session)
    created = await ApiKeyService(db_session).generate_key(
        user.id,
        name="Sandbox",
        environment=ApiKeyEnvironment.SANDBOX,
    )
    fake_redis.values[f"apikey_cache:{created.api_key.key_prefix}"] = (
        f"{user.id}:{created.api_key.id}"
    )

    revoked = await ApiKeyService(db_session).revoke_key(
        created.api_key.id,
        user.id,
        reason="not needed",
    )

    assert revoked.is_active is False
    assert revoked.revoked_reason == "not needed"
    assert f"apikey_cache:{created.api_key.key_prefix}" not in fake_redis.values
    assert await ApiKeyRepository(db_session).validate_key(created.raw_key) is None


async def test_generate_key_enforces_active_key_limit(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    service = ApiKeyService(db_session)

    for index in range(MAX_ACTIVE_KEYS):
        await service.generate_key(
            user.id,
            name=f"Key {index}",
            environment=ApiKeyEnvironment.SANDBOX,
        )

    with pytest.raises(ApiKeyLimitError):
        await service.generate_key(
            user.id,
            name="One too many",
            environment=ApiKeyEnvironment.SANDBOX,
        )


async def test_expire_stale_keys_marks_expired_key_inactive(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    created = await ApiKeyService(db_session).generate_key(
        user.id,
        name="Temporary",
        environment=ApiKeyEnvironment.SANDBOX,
    )
    created.api_key.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.commit()

    count = await ApiKeyRepository(db_session).expire_stale_keys()

    assert count == 1
    assert created.api_key.is_active is False
    assert created.api_key.revoked_reason == "expired"
