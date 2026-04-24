import asyncio
import os
import re
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
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_bay_test"
)
os.environ["DATABASE_URL_SYNC"] = (
    "postgresql+psycopg2://postgres:postgres@localhost:5432/agentic_bay_test"
)
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.api.routes.auth.email import get_email_otp_provider
from app.auth.otp_store import (
    OTPExpiredError,
    OTPInvalidCodeError,
    OTPStore,
    OTPTooManyAttemptsError,
    generate_otp_code,
)
from app.auth.providers.email_otp import (
    CircleWalletService,
    EmailDelivery,
    EmailMessage,
    EmailOTPProvider,
)
from app.auth.rate_limiter import OTPSendRateLimiter
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


class FakeRedis:
    def __init__(self):
        self._values: dict[str, str] = {}
        self._expires_at: dict[str, int] = {}
        self.now = 0

    def advance(self, seconds: int) -> None:
        self.now += seconds

    def _purge_if_expired(self, key: str) -> None:
        expires_at = self._expires_at.get(key)
        if expires_at is not None and expires_at <= self.now:
            self._values.pop(key, None)
            self._expires_at.pop(key, None)

    async def get(self, key: str) -> str | None:
        self._purge_if_expired(key)
        return self._values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._values[key] = value
        if ex is not None:
            self._expires_at[key] = self.now + ex
        else:
            self._expires_at.pop(key, None)
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            self._purge_if_expired(key)
            if key in self._values:
                deleted += 1
            self._values.pop(key, None)
            self._expires_at.pop(key, None)
        return deleted

    async def exists(self, key: str) -> int:
        self._purge_if_expired(key)
        return int(key in self._values)

    async def ttl(self, key: str) -> int:
        self._purge_if_expired(key)
        if key not in self._values:
            return -2
        expires_at = self._expires_at.get(key)
        if expires_at is None:
            return -1
        return max(0, expires_at - self.now)

    async def incr(self, key: str) -> int:
        self._purge_if_expired(key)
        current = int(self._values.get(key, "0")) + 1
        self._values[key] = str(current)
        return current

    async def expire(self, key: str, seconds: int) -> bool:
        self._purge_if_expired(key)
        if key not in self._values:
            return False
        self._expires_at[key] = self.now + seconds
        return True


class FakeEmailDelivery(EmailDelivery):
    def __init__(self):
        self.messages: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.messages.append(message)


class FakeCircleWalletService(CircleWalletService):
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    async def create_wallet_for_user(self, user_id: str, email: str) -> None:
        self.calls.append((user_id, email))


def build_user(
    *,
    email: str = "user@example.com",
    role: str = "BUYER",
    email_verified: bool = True,
    auth_provider: str | None = "EMAIL",
) -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        email=email,
        display_name=None,
        role=role,
        email_verified=email_verified,
        auth_provider=auth_provider,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def build_provider(
    *,
    users: list[User] | None = None,
) -> tuple[
    EmailOTPProvider,
    FakeAsyncSessionStore,
    FakeRedis,
    FakeEmailDelivery,
    FakeCircleWalletService,
]:
    db = FakeAsyncSessionStore(users=users)
    redis = FakeRedis()
    email_delivery = FakeEmailDelivery()
    wallet_service = FakeCircleWalletService()
    provider = EmailOTPProvider(
        db=db,
        otp_store=OTPStore(redis),
        rate_limiter=OTPSendRateLimiter(redis),
        email_delivery=email_delivery,
        circle_wallet_service=wallet_service,
    )
    return provider, db, redis, email_delivery, wallet_service


def extract_code(message: EmailMessage) -> str:
    match = re.search(r"\b(\d{6})\b", message.body)
    assert match is not None
    return match.group(1)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_generate_otp_code_returns_exactly_six_digits() -> None:
    code = generate_otp_code()

    assert len(code) == 6
    assert code.isdigit()


@pytest.mark.asyncio
async def test_otp_store_deletes_code_immediately_after_successful_verification() -> None:
    redis = FakeRedis()
    store = OTPStore(redis)
    code = "847291"

    await store.store_code("user@example.com", code)
    assert await store.code_exists("user@example.com")

    await store.verify_code("user@example.com", code)

    assert not await store.code_exists("user@example.com")


@pytest.mark.asyncio
async def test_otp_store_invalidates_code_after_five_failed_attempts() -> None:
    redis = FakeRedis()
    store = OTPStore(redis)
    await store.store_code("user@example.com", "847291")

    for _ in range(4):
        with pytest.raises(OTPInvalidCodeError):
            await store.verify_code("user@example.com", "000000")

    with pytest.raises(OTPTooManyAttemptsError):
        await store.verify_code("user@example.com", "000000")

    assert not await store.code_exists("user@example.com")


@pytest.mark.asyncio
async def test_otp_store_rejects_expired_codes_after_ten_minutes() -> None:
    redis = FakeRedis()
    store = OTPStore(redis)
    await store.store_code("user@example.com", "847291")
    redis.advance(601)

    with pytest.raises(OTPExpiredError):
        await store.verify_code("user@example.com", "847291")


def test_send_otp_endpoint_rate_limits_the_fourth_request_and_returns_retry_after() -> None:
    provider, _, _, email_delivery, _ = build_provider()

    async def fake_get_email_otp_provider() -> EmailOTPProvider:
        return provider

    app.dependency_overrides[get_email_otp_provider] = fake_get_email_otp_provider
    client = TestClient(app)

    for _ in range(3):
        response = client.post(
            "/api/auth/email/send-otp",
            json={"email": "User@example.com"},
        )
        assert response.status_code == 200

    blocked_response = client.post(
        "/api/auth/email/send-otp",
        json={"email": "User@example.com"},
    )

    assert blocked_response.status_code == 429
    assert blocked_response.json()["detail"] == "Too many OTP requests. Try again later."
    assert blocked_response.json()["retry_after"] == 900
    assert blocked_response.headers["Retry-After"] == "900"
    assert len(email_delivery.messages) == 3


def test_verify_otp_endpoint_creates_new_user_and_triggers_circle_wallet() -> None:
    provider, db, _, email_delivery, wallet_service = build_provider()

    async def fake_get_email_otp_provider() -> EmailOTPProvider:
        return provider

    app.dependency_overrides[get_email_otp_provider] = fake_get_email_otp_provider
    client = TestClient(app)

    send_response = client.post(
        "/api/auth/email/send-otp",
        json={"email": "  NewUser@example.com  "},
    )
    assert send_response.status_code == 200
    assert send_response.json()["email"] == "newuser@example.com"
    assert email_delivery.messages[0].subject == "Your sign-in code for Agentic Bay"

    code = extract_code(email_delivery.messages[0])
    verify_response = client.post(
        "/api/auth/email/verify-otp",
        json={"email": "newuser@example.com", "code": code},
        headers={"user-agent": "Mozilla/5.0", "x-forwarded-for": "198.51.100.8"},
    )

    assert verify_response.status_code == 200
    body = verify_response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 86400
    assert body["user"]["email"] == "newuser@example.com"
    assert body["user"]["display_name"] is None
    assert body["user"]["role"] == "BUYER"
    assert body["user"]["is_new_user"] is True

    created_user = next(iter(db.users.values()))
    assert created_user.email_verified is True
    assert created_user.auth_provider == "EMAIL"
    assert wallet_service.calls == [(str(created_user.id), created_user.email)]
    assert len(db.sessions) == 1
    assert not asyncio.run(provider.otp_store.code_exists(created_user.email))

    second_verify = client.post(
        "/api/auth/email/verify-otp",
        json={"email": "newuser@example.com", "code": code},
    )
    assert second_verify.status_code == 401
    assert second_verify.json()["detail"] == "OTP code has expired. Request a new code."


def test_verify_otp_logs_in_existing_user_regardless_of_provider() -> None:
    existing_user = build_user(
        email="user@example.com",
        email_verified=False,
        auth_provider="GOOGLE",
    )
    provider, db, _, email_delivery, wallet_service = build_provider(users=[existing_user])

    async def fake_get_email_otp_provider() -> EmailOTPProvider:
        return provider

    app.dependency_overrides[get_email_otp_provider] = fake_get_email_otp_provider
    client = TestClient(app)

    send_response = client.post(
        "/api/auth/email/send-otp",
        json={"email": "user@example.com"},
    )
    assert send_response.status_code == 200
    code = extract_code(email_delivery.messages[0])

    verify_response = client.post(
        "/api/auth/email/verify-otp",
        json={"email": "user@example.com", "code": code},
    )

    assert verify_response.status_code == 200
    body = verify_response.json()
    assert body["user"]["id"] == str(existing_user.id)
    assert body["user"]["is_new_user"] is False
    assert wallet_service.calls == []
    assert db.users[existing_user.id].auth_provider == "GOOGLE"
    assert db.users[existing_user.id].email_verified is True
    assert len(db.sessions) == 1


def test_verify_otp_endpoint_rejects_expired_codes() -> None:
    provider, _, redis, email_delivery, _ = build_provider()

    async def fake_get_email_otp_provider() -> EmailOTPProvider:
        return provider

    app.dependency_overrides[get_email_otp_provider] = fake_get_email_otp_provider
    client = TestClient(app)

    send_response = client.post(
        "/api/auth/email/send-otp",
        json={"email": "user@example.com"},
    )
    assert send_response.status_code == 200
    code = extract_code(email_delivery.messages[0])
    redis.advance(601)

    verify_response = client.post(
        "/api/auth/email/verify-otp",
        json={"email": "user@example.com", "code": code},
    )

    assert verify_response.status_code == 401
    assert verify_response.json()["detail"] == "OTP code has expired. Request a new code."
