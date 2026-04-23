import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_keys import ApiKeyEnvironment
from app.models.users import UserRole, UserStatus
from app.repositories.api_key_repo import ApiKeyRepository
from app.repositories.user_repo import UserRepository
from tests.conftest import make_user

try:
    from app.core.security import hash_password
except Exception:
    from passlib.context import CryptContext

    _ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(p: str) -> str:  # type: ignore[misc]
        return _ctx.hash(p)


# ── create ────────────────────────────────────────────────────────────────────

async def test_create_user(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    user = await repo.create(
        email="alice@example.com",
        role=UserRole.BUYER,
        status=UserStatus.ACTIVE,
        email_verified=False,
        kyc_verified=False,
        notification_preferences={},
    )
    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.role == UserRole.BUYER
    assert user.status == UserStatus.ACTIVE
    assert user.email_verified is False


async def test_create_sets_defaults(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    assert user.status == UserStatus.ACTIVE
    assert user.email_verified is False
    assert user.kyc_verified is False


# ── get_by_id ─────────────────────────────────────────────────────────────────

async def test_get_by_id_returns_user(db_session: AsyncSession) -> None:
    created = await make_user(db_session, email="bob@example.com")
    repo = UserRepository(db_session)
    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.email == "bob@example.com"


async def test_get_by_id_unknown_returns_none(db_session: AsyncSession) -> None:
    repo = UserRepository(db_session)
    assert await repo.get_by_id(uuid.uuid4()) is None


# ── get_by_email ──────────────────────────────────────────────────────────────

async def test_get_by_email_found(db_session: AsyncSession) -> None:
    await make_user(db_session, email="charlie@example.com")
    user = await UserRepository(db_session).get_by_email("charlie@example.com")
    assert user is not None
    assert user.email == "charlie@example.com"


async def test_get_by_email_not_found(db_session: AsyncSession) -> None:
    result = await UserRepository(db_session).get_by_email("nobody@example.com")
    assert result is None


# ── get_by_wallet_address ─────────────────────────────────────────────────────

async def test_get_by_wallet_address_found(db_session: AsyncSession) -> None:
    await make_user(db_session, wallet_address="0xDEAD")
    user = await UserRepository(db_session).get_by_wallet_address("0xDEAD")
    assert user is not None
    assert user.wallet_address == "0xDEAD"


async def test_get_by_wallet_address_not_found(db_session: AsyncSession) -> None:
    result = await UserRepository(db_session).get_by_wallet_address("0xBAD")
    assert result is None


# ── update ────────────────────────────────────────────────────────────────────

async def test_update_fields(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    repo = UserRepository(db_session)
    updated = await repo.update(user.id, display_name="New Name", email_verified=True)
    assert updated is not None
    assert updated.display_name == "New Name"
    assert updated.email_verified is True


async def test_update_unknown_returns_none(db_session: AsyncSession) -> None:
    result = await UserRepository(db_session).update(uuid.uuid4(), display_name="X")
    assert result is None


# ── delete ────────────────────────────────────────────────────────────────────

async def test_delete_removes_user(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    repo = UserRepository(db_session)
    assert await repo.delete(user.id) is True
    assert await repo.get_by_id(user.id) is None


async def test_delete_unknown_returns_false(db_session: AsyncSession) -> None:
    assert await UserRepository(db_session).delete(uuid.uuid4()) is False


# ── exists ────────────────────────────────────────────────────────────────────

async def test_exists_true(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    assert await UserRepository(db_session).exists(user.id) is True


async def test_exists_false(db_session: AsyncSession) -> None:
    assert await UserRepository(db_session).exists(uuid.uuid4()) is False


# ── get_all ───────────────────────────────────────────────────────────────────

async def test_get_all_returns_all(db_session: AsyncSession) -> None:
    await make_user(db_session)
    await make_user(db_session)
    users = await UserRepository(db_session).get_all()
    assert len(users) == 2


async def test_get_all_respects_limit(db_session: AsyncSession) -> None:
    for _ in range(5):
        await make_user(db_session)
    users = await UserRepository(db_session).get_all(limit=3)
    assert len(users) == 3


async def test_get_all_empty(db_session: AsyncSession) -> None:
    assert await UserRepository(db_session).get_all() == []


# ── get_by_api_key ────────────────────────────────────────────────────────────

async def test_get_by_api_key_success(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    raw_key = "abcdefgh12345678"
    await ApiKeyRepository(db_session).create(
        user_id=user.id,
        name="My Key",
        key_prefix=raw_key[:8],
        key_hash=hash_password(raw_key),
        environment=ApiKeyEnvironment.SANDBOX,
        permissions=[],
        is_active=True,
    )
    found = await UserRepository(db_session).get_by_api_key(raw_key)
    assert found is not None
    assert found.id == user.id


async def test_get_by_api_key_wrong_key_returns_none(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    raw_key = "abcdefgh12345678"
    await ApiKeyRepository(db_session).create(
        user_id=user.id,
        name="My Key",
        key_prefix=raw_key[:8],
        key_hash=hash_password(raw_key),
        environment=ApiKeyEnvironment.SANDBOX,
        permissions=[],
        is_active=True,
    )
    # Same prefix, different suffix → bcrypt check fails
    found = await UserRepository(db_session).get_by_api_key("abcdefghWRONGSFX")
    assert found is None
