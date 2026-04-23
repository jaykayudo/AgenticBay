import asyncio
import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.sql import operators
from sqlalchemy.sql.elements import BindParameter

os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_bay_test"
os.environ["DATABASE_URL_SYNC"] = (
    "postgresql+psycopg2://postgres:postgres@localhost:5432/agentic_bay_test"
)
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.api.deps import get_session
from app.auth.jwt import create_access_token, decode_access_token
from app.auth.session_manager import RefreshTokenReuseDetectedError, SessionManager
from app.main import app
from app.models.auth_session import AuthSession
from app.models.user import User


class FakeScalarResult:
    def __init__(self, items: list[Any]):
        self._items = items

    def __iter__(self):
        return iter(self._items)


class FakeAsyncSessionStore:
    def __init__(
        self,
        *,
        users: list[User] | None = None,
        sessions: list[AuthSession] | None = None,
    ):
        self.users = {user.id: user for user in users or []}
        self.sessions = {session.id: session for session in sessions or []}

    def add(self, obj: Any) -> None:
        now = datetime.now(UTC)
        if isinstance(obj, AuthSession):
            if obj.id is None:
                obj.id = uuid4()
            if obj.created_at is None:
                obj.created_at = now
            if obj.updated_at is None:
                obj.updated_at = now
            obj.user = self.users[obj.user_id]
            self.sessions[obj.id] = obj
        elif isinstance(obj, User):
            if obj.id is None:
                obj.id = uuid4()
            if obj.created_at is None:
                obj.created_at = now
            if obj.updated_at is None:
                obj.updated_at = now
            self.users[obj.id] = obj

    async def flush(self) -> None:
        return None

    async def get(self, model: type[Any], key: Any) -> Any | None:
        if model is User:
            return self.users.get(key)
        return None

    async def scalar(self, statement: Any) -> Any | None:
        items = self._filter(statement)
        return items[0] if items else None

    async def scalars(self, statement: Any) -> FakeScalarResult:
        return FakeScalarResult(self._filter(statement))

    def _filter(self, statement: Any) -> list[Any]:
        entity = statement.column_descriptions[0]["entity"]
        if entity is AuthSession:
            items: list[Any] = list(self.sessions.values())
        elif entity is User:
            items = list(self.users.values())
        else:
            items = []

        for criterion in statement._where_criteria:
            items = [item for item in items if self._matches(item, criterion)]

        return items

    @staticmethod
    def _matches(item: Any, criterion: Any) -> bool:
        column_name = getattr(getattr(criterion, "left", None), "key", None)
        operator = getattr(criterion, "operator", None)
        value = FakeAsyncSessionStore._resolve_value(getattr(criterion, "right", None))

        if column_name is None or operator is None:
            raise AssertionError(f"Unsupported SQLAlchemy criterion in test double: {criterion!r}")

        item_value = getattr(item, column_name)
        if operator is operators.eq:
            return item_value == value
        if operator is operators.gt:
            return item_value > value
        if operator is operators.is_:
            return item_value is value

        raise AssertionError(f"Unsupported SQLAlchemy operator in test double: {criterion!r}")

    @staticmethod
    def _resolve_value(value: Any) -> Any:
        if isinstance(value, BindParameter):
            return value.value
        if hasattr(value, "value"):
            return value.value
        rendered = str(value).lower()
        if rendered == "true":
            return True
        if rendered == "false":
            return False
        return value


def build_user(*, email: str = "user@example.com", role: str = "member") -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        email=email,
        role=role,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_issue_tokens_encodes_user_identity_and_hashes_refresh_token() -> None:
    user = build_user()
    store = FakeAsyncSessionStore(users=[user])
    manager = SessionManager(store)

    tokens = await manager.issue_tokens(
        user=user,
        device_info="Mozilla/5.0",
        ip_address="127.0.0.1",
    )

    claims = decode_access_token(tokens.access_token)
    stored_session = store.sessions[tokens.session.id]

    assert claims.sub == str(user.id)
    assert claims.email == user.email
    assert claims.role == user.role
    assert claims.sid == str(tokens.session.id)
    assert tokens.expires_in == 86400
    assert tokens.refresh_token.startswith("rt_")
    assert stored_session.refresh_token_hash != tokens.refresh_token
    assert stored_session.refresh_token_prefix == f"rt_{tokens.refresh_token[3:11]}..."


@pytest.mark.asyncio
async def test_refresh_rotation_marks_old_session_inactive_and_creates_new_session() -> None:
    user = build_user()
    store = FakeAsyncSessionStore(users=[user])
    manager = SessionManager(store)

    original = await manager.issue_tokens(
        user=user,
        device_info="Mozilla/5.0",
        ip_address="127.0.0.1",
    )

    refreshed = await manager.refresh_tokens(
        refresh_token=original.refresh_token,
        device_info="Mozilla/5.0 (refreshed)",
        ip_address="127.0.0.2",
    )

    old_session = store.sessions[original.session.id]
    new_session = store.sessions[refreshed.session.id]
    claims = decode_access_token(refreshed.access_token)

    assert refreshed.refresh_token != original.refresh_token
    assert old_session.is_active is False
    assert old_session.revoked_reason == "rotated"
    assert new_session.is_active is True
    assert new_session.rotated_from_session_id == old_session.id
    assert new_session.device_info == "Mozilla/5.0 (refreshed)"
    assert new_session.ip_address == "127.0.0.2"
    assert claims.sub == str(user.id)
    assert claims.email == user.email
    assert claims.role == user.role


@pytest.mark.asyncio
async def test_refresh_token_reuse_detection_invalidates_all_active_sessions() -> None:
    user = build_user()
    store = FakeAsyncSessionStore(users=[user])
    manager = SessionManager(store)

    original = await manager.issue_tokens(
        user=user,
        device_info="Device A",
        ip_address="10.0.0.1",
    )
    await manager.refresh_tokens(
        refresh_token=original.refresh_token,
        device_info="Device A",
        ip_address="10.0.0.1",
    )
    other_session = await manager.issue_tokens(
        user=user,
        device_info="Device B",
        ip_address="10.0.0.2",
    )

    with pytest.raises(RefreshTokenReuseDetectedError):
        await manager.refresh_tokens(
            refresh_token=original.refresh_token,
            device_info="Attacker",
            ip_address="203.0.113.10",
        )

    assert store.sessions[other_session.session.id].is_active is False
    assert store.sessions[other_session.session.id].revoked_reason == "reuse_detected"
    active_sessions = [session for session in store.sessions.values() if session.is_active]
    assert active_sessions == []


def test_me_endpoint_returns_profile_and_expired_token_returns_401() -> None:
    user = build_user()
    store = FakeAsyncSessionStore(users=[user])
    manager = SessionManager(store)
    tokens = asyncio.run(
        manager.issue_tokens(
            user=user,
            device_info="Browser",
            ip_address="127.0.0.1",
        )
    )

    async def fake_get_session() -> Any:
        yield store

    app.dependency_overrides[get_session] = fake_get_session

    client = TestClient(app)
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == user.email
    assert response.json()["role"] == user.role

    expired_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        session_id=tokens.session.id,
        expires_in_seconds=-5,
    )
    expired_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert expired_response.status_code == 401
    assert expired_response.json()["detail"] == "Access token has expired."


def test_session_endpoints_support_listing_refresh_logout_and_logout_all() -> None:
    user = build_user()
    store = FakeAsyncSessionStore(users=[user])
    manager = SessionManager(store)
    current = asyncio.run(
        manager.issue_tokens(
            user=user,
            device_info="Current Browser",
            ip_address="127.0.0.1",
        )
    )
    other = asyncio.run(
        manager.issue_tokens(
            user=user,
            device_info="Other Browser",
            ip_address="127.0.0.2",
        )
    )

    async def fake_get_session() -> Any:
        yield store

    app.dependency_overrides[get_session] = fake_get_session

    client = TestClient(app)
    sessions_response = client.get(
        "/api/auth/sessions",
        headers={"Authorization": f"Bearer {current.access_token}"},
    )

    assert sessions_response.status_code == 200
    sessions = sessions_response.json()["sessions"]
    assert len(sessions) == 2
    assert sum(session["is_current"] for session in sessions) == 1

    revoke_response = client.delete(
        f"/api/auth/sessions/{other.session.id}",
        headers={"Authorization": f"Bearer {current.access_token}"},
    )
    assert revoke_response.status_code == 204
    assert store.sessions[other.session.id].is_active is False

    refresh_response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": current.refresh_token},
        headers={"user-agent": "Rotated Browser", "x-forwarded-for": "198.51.100.20"},
    )
    assert refresh_response.status_code == 200
    refreshed_body = refresh_response.json()
    assert refreshed_body["refresh_token"] != current.refresh_token
    assert refreshed_body["expires_in"] == 86400
    assert store.sessions[current.session.id].is_active is False
    new_session_ids = [
        session_id for session_id in store.sessions if session_id != current.session.id
    ]
    assert any(store.sessions[session_id].is_active for session_id in new_session_ids)

    logout_response = client.post(
        "/api/auth/logout",
        json={"refresh_token": refreshed_body["refresh_token"]},
    )
    assert logout_response.status_code == 204

    logout_all_response = client.post(
        "/api/auth/logout-all",
        headers={"Authorization": f"Bearer {current.access_token}"},
    )
    assert logout_all_response.status_code == 200
    assert logout_all_response.json()["revoked_sessions"] >= 0
    assert [session for session in store.sessions.values() if session.is_active] == []


def test_refresh_endpoint_returns_401_and_revokes_all_sessions_on_reuse() -> None:
    user = build_user()
    store = FakeAsyncSessionStore(users=[user])
    manager = SessionManager(store)
    original = asyncio.run(
        manager.issue_tokens(
            user=user,
            device_info="Primary",
            ip_address="127.0.0.1",
        )
    )
    asyncio.run(
        manager.refresh_tokens(
            refresh_token=original.refresh_token,
            device_info="Primary",
            ip_address="127.0.0.1",
        )
    )
    asyncio.run(
        manager.issue_tokens(
            user=user,
            device_info="Secondary",
            ip_address="127.0.0.2",
        )
    )

    async def fake_get_session() -> Any:
        yield store

    app.dependency_overrides[get_session] = fake_get_session

    client = TestClient(app)
    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": original.refresh_token},
    )

    assert response.status_code == 401
    assert (
        response.json()["detail"]
        == "Refresh token reuse detected. All sessions have been invalidated."
    )
    assert [session for session in store.sessions.values() if session.is_active] == []


def test_refresh_endpoint_rejects_revoked_refresh_tokens() -> None:
    user = build_user()
    store = FakeAsyncSessionStore(users=[user])
    manager = SessionManager(store)
    issued = asyncio.run(
        manager.issue_tokens(
            user=user,
            device_info="Browser",
            ip_address="127.0.0.1",
        )
    )

    async def fake_get_session() -> Any:
        yield store

    app.dependency_overrides[get_session] = fake_get_session

    client = TestClient(app)
    logout_response = client.post(
        "/api/auth/logout",
        json={"refresh_token": issued.refresh_token},
    )
    assert logout_response.status_code == 204

    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": issued.refresh_token},
    )

    assert response.status_code == 401
    assert (
        response.json()["detail"]
        == "Refresh token reuse detected. All sessions have been invalidated."
    )
