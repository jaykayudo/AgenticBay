from __future__ import annotations

import uuid

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.auth.jwt import create_access_token
from app.main import app
from app.models.users import UserRole
from tests.conftest import make_user


@pytest.fixture(autouse=True)
def clear_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


async def _override_db(db_session: AsyncSession):
    async def get_test_session():
        yield db_session

    app.dependency_overrides[get_session] = get_test_session


def _token_for(user_id: uuid.UUID, email: str) -> str:
    return create_access_token(
        user_id=user_id,
        email=email,
        role=UserRole.BUYER,
        session_id=uuid.uuid4(),
    )


@pytest.mark.asyncio
async def test_create_and_list_api_keys(db_session: AsyncSession) -> None:
    user = await make_user(db_session, email="keys@example.com", role=UserRole.BUYER)
    await _override_db(db_session)
    token = _token_for(user.id, user.email)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/api/keys",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Production Backend",
                "environment": "PRODUCTION",
                "permissions": ["search", "hire"],
            },
        )
        listed = await client.get("/api/keys", headers={"Authorization": f"Bearer {token}"})

    assert created.status_code == 201
    created_body = created.json()
    assert created_body["key"].startswith("mk_live_")
    assert created_body["key_prefix"] == created_body["key"][:16]
    assert "key_hash" not in created_body

    assert listed.status_code == 200
    listed_body = listed.json()
    assert len(listed_body) == 1
    assert listed_body[0]["key_prefix"] == created_body["key_prefix"]
    assert "key" not in listed_body[0]
    assert "key_hash" not in listed_body[0]


@pytest.mark.asyncio
async def test_revoke_api_key_removes_it_from_active_validation(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session, email="revoke@example.com", role=UserRole.BUYER)
    await _override_db(db_session)
    token = _token_for(user.id, user.email)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/api/keys",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Sandbox", "environment": "SANDBOX"},
        )
        key_id = created.json()["id"]
        revoked = await client.request(
            "DELETE",
            f"/api/keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "rotated elsewhere"},
        )
        fetched = await client.get(
            f"/api/keys/{key_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert revoked.status_code == 204
    assert fetched.status_code == 200
    assert fetched.json()["is_active"] is False
    assert fetched.json()["revoked_reason"] == "rotated elsewhere"
