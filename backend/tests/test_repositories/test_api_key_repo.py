import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.api_keys import ApiKeyEnvironment
from app.repositories.api_key_repo import ApiKeyRepository
from tests.conftest import make_user


def _make_raw_key(prefix: str = "abcdefgh") -> str:
    """Return a 24-char raw API key with a recognisable prefix."""
    return prefix + uuid.uuid4().hex[:16]


async def _create_key(db_session: AsyncSession, user_id: uuid.UUID, raw_key: str, **kwargs):
    defaults = dict(
        user_id=user_id,
        name="Test Key",
        key_prefix=raw_key[:8],
        key_hash=hash_password(raw_key),
        environment=ApiKeyEnvironment.SANDBOX,
        permissions=[],
        is_active=True,
    )
    defaults.update(kwargs)
    return await ApiKeyRepository(db_session).create(**defaults)


# ── create ────────────────────────────────────────────────────────────────────

async def test_create_api_key(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    raw_key = _make_raw_key()
    key = await _create_key(db_session, user.id, raw_key)
    assert key.id is not None
    assert key.key_prefix == raw_key[:8]
    assert key.is_active is True
    # Hash must NOT equal the plain key
    assert key.key_hash != raw_key
    assert verify_password(raw_key, key.key_hash)


# ── get_user_keys ─────────────────────────────────────────────────────────────

async def test_get_user_keys_returns_active_by_default(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    active_key = await _create_key(db_session, user.id, _make_raw_key(), is_active=True)
    revoked_key = await _create_key(db_session, user.id, _make_raw_key(), is_active=False)

    repo = ApiKeyRepository(db_session)
    keys = await repo.get_user_keys(user.id)
    ids = {k.id for k in keys}
    assert active_key.id in ids
    assert revoked_key.id not in ids


async def test_get_user_keys_active_only_false_returns_all(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    await _create_key(db_session, user.id, _make_raw_key(), is_active=True)
    await _create_key(db_session, user.id, _make_raw_key(), is_active=False)

    keys = await ApiKeyRepository(db_session).get_user_keys(user.id, active_only=False)
    assert len(keys) == 2


async def test_get_user_keys_only_own_keys(db_session: AsyncSession) -> None:
    user1 = await make_user(db_session)
    user2 = await make_user(db_session)
    await _create_key(db_session, user1.id, _make_raw_key())
    await _create_key(db_session, user2.id, _make_raw_key())

    keys = await ApiKeyRepository(db_session).get_user_keys(user1.id)
    assert len(keys) == 1
    assert keys[0].user_id == user1.id


async def test_get_user_keys_empty(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    assert await ApiKeyRepository(db_session).get_user_keys(user.id) == []


# ── revoke ────────────────────────────────────────────────────────────────────

async def test_revoke_sets_inactive(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    key = await _create_key(db_session, user.id, _make_raw_key())
    repo = ApiKeyRepository(db_session)

    revoked = await repo.revoke(key.id)
    assert revoked is not None
    assert revoked.is_active is False


async def test_revoke_key_no_longer_returned_by_get_user_keys(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    raw_key = _make_raw_key()
    key = await _create_key(db_session, user.id, raw_key)

    repo = ApiKeyRepository(db_session)
    await repo.revoke(key.id)
    active_keys = await repo.get_user_keys(user.id)
    assert active_keys == []


async def test_revoke_unknown_returns_none(db_session: AsyncSession) -> None:
    result = await ApiKeyRepository(db_session).revoke(uuid.uuid4())
    assert result is None


# ── validate_key ──────────────────────────────────────────────────────────────

async def test_validate_key_success_returns_key(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    raw_key = _make_raw_key()
    await _create_key(db_session, user.id, raw_key)

    result = await ApiKeyRepository(db_session).validate_key(raw_key)
    assert result is not None
    assert result.key_prefix == raw_key[:8]


async def test_validate_key_updates_last_used_at(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    raw_key = _make_raw_key()
    key = await _create_key(db_session, user.id, raw_key)
    assert key.last_used_at is None

    await ApiKeyRepository(db_session).validate_key(raw_key)
    # Re-fetch to confirm the DB value was written
    from app.repositories.base import BaseRepository
    from app.models.api_keys import ApiKey
    refreshed = await db_session.get(ApiKey, key.id)
    assert refreshed is not None
    assert refreshed.last_used_at is not None


async def test_validate_key_wrong_secret_returns_none(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    raw_key = _make_raw_key("abcdefgh")
    await _create_key(db_session, user.id, raw_key)

    # Same 8-char prefix, different tail — bcrypt check must fail
    wrong_key = "abcdefgh" + "X" * 16
    result = await ApiKeyRepository(db_session).validate_key(wrong_key)
    assert result is None


async def test_validate_key_revoked_returns_none(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    raw_key = _make_raw_key()
    key = await _create_key(db_session, user.id, raw_key)

    await ApiKeyRepository(db_session).revoke(key.id)
    result = await ApiKeyRepository(db_session).validate_key(raw_key)
    assert result is None


async def test_validate_key_no_matching_prefix_returns_none(db_session: AsyncSession) -> None:
    result = await ApiKeyRepository(db_session).validate_key("zzzzzzzz99999999")
    assert result is None
