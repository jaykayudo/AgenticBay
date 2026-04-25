"""
Unit tests for PATCH /api/auth/auto-pay endpoint.
"""

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_bay_test"
)
os.environ.setdefault(
    "DATABASE_URL_SYNC", "postgresql+psycopg2://postgres:postgres@localhost:5432/agentic_bay_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.api.dependencies.auth import get_current_user
from app.main import app
from app.models.users import User, UserRole, UserStatus


def _make_user(auto_pay_enabled: bool = False) -> User:
    now = datetime.now(UTC)
    user = User(
        id=uuid4(),
        email="test@example.com",
        role=UserRole.BUYER,
        status=UserStatus.ACTIVE,
        email_verified=True,
        created_at=now,
        updated_at=now,
    )
    user.auto_pay_enabled = auto_pay_enabled  # type: ignore[attr-defined]
    user.auto_pay_max_per_job = None  # type: ignore[attr-defined]
    user.auto_pay_max_per_day = None  # type: ignore[attr-defined]
    return user


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_patch_auto_pay_updates_settings() -> None:
    user = _make_user()
    committed: list[dict] = []

    class FakeDB:
        async def commit(self) -> None:
            committed.append(
                {
                    "auto_pay_enabled": user.auto_pay_enabled,
                    "per_job": str(user.auto_pay_max_per_job),
                    "per_day": str(user.auto_pay_max_per_day),
                }
            )

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

    async def fake_user():
        return user

    async def fake_db():
        return FakeDB()

    from app.api.deps import get_session

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_session] = fake_db

    client = TestClient(app)
    response = client.patch(
        "/api/auth/auto-pay",
        json={"auto_pay_enabled": True, "auto_pay_max_per_job": 5.0, "auto_pay_max_per_day": 20.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["auto_pay_enabled"] is True
    assert body["auto_pay_max_per_job"] == 5.0
    assert body["auto_pay_max_per_day"] == 20.0


def test_get_auto_pay_returns_current_settings() -> None:
    from decimal import Decimal

    user = _make_user(auto_pay_enabled=True)
    user.auto_pay_max_per_job = Decimal("3.5")  # type: ignore[attr-defined]
    user.auto_pay_max_per_day = Decimal("30.0")  # type: ignore[attr-defined]

    async def fake_user():
        return user

    app.dependency_overrides[get_current_user] = fake_user

    client = TestClient(app)
    response = client.get("/api/auth/auto-pay")

    assert response.status_code == 200
    body = response.json()
    assert body["auto_pay_enabled"] is True
    assert body["auto_pay_max_per_job"] == 3.5
    assert body["auto_pay_max_per_day"] == 30.0
