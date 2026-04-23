import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agents import AgentStatus
from app.repositories.agent_repo import AgentRepository
from tests.conftest import make_agent, make_user


# ── create ────────────────────────────────────────────────────────────────────

async def test_create_agent_generates_orchestrator_key(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    assert agent.id is not None
    # Key is auto-generated at creation time
    assert agent.orchestrator_api_key is not None
    assert len(agent.orchestrator_api_key) > 0


async def test_create_two_agents_have_unique_keys(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    a1 = await make_agent(db_session, user.id)
    a2 = await make_agent(db_session, user.id)
    assert a1.orchestrator_api_key != a2.orchestrator_api_key


# ── get_by_slug ───────────────────────────────────────────────────────────────

async def test_get_by_slug_found(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    await make_agent(db_session, user.id, slug="my-slug")
    agent = await AgentRepository(db_session).get_by_slug("my-slug")
    assert agent is not None
    assert agent.slug == "my-slug"


async def test_get_by_slug_not_found(db_session: AsyncSession) -> None:
    result = await AgentRepository(db_session).get_by_slug("nonexistent")
    assert result is None


# ── get_active_agents ─────────────────────────────────────────────────────────

async def test_get_active_agents_returns_only_active(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    await make_agent(db_session, user.id, status=AgentStatus.ACTIVE)
    await make_agent(db_session, user.id, status=AgentStatus.PENDING)
    await make_agent(db_session, user.id, status=AgentStatus.PAUSED)
    agents = await AgentRepository(db_session).get_active_agents()
    assert len(agents) == 1
    assert agents[0].status == AgentStatus.ACTIVE


async def test_get_active_agents_empty(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    await make_agent(db_session, user.id, status=AgentStatus.PENDING)
    agents = await AgentRepository(db_session).get_active_agents()
    assert agents == []


async def test_get_active_agents_respects_limit(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    for _ in range(5):
        await make_agent(db_session, user.id, status=AgentStatus.ACTIVE)
    agents = await AgentRepository(db_session).get_active_agents(limit=2)
    assert len(agents) == 2


# ── get_by_owner ──────────────────────────────────────────────────────────────

async def test_get_by_owner_returns_owned_agents(db_session: AsyncSession) -> None:
    owner1 = await make_user(db_session)
    owner2 = await make_user(db_session)
    await make_agent(db_session, owner1.id)
    await make_agent(db_session, owner1.id)
    await make_agent(db_session, owner2.id)
    owned = await AgentRepository(db_session).get_by_owner(owner1.id)
    assert len(owned) == 2
    assert all(a.owner_id == owner1.id for a in owned)


async def test_get_by_owner_no_agents(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    owned = await AgentRepository(db_session).get_by_owner(user.id)
    assert owned == []


# ── update_stats ──────────────────────────────────────────────────────────────

async def test_update_stats_fields(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    repo = AgentRepository(db_session)
    updated = await repo.update_stats(
        agent.id,
        total_jobs=42,
        success_rate=Decimal("95.50"),
        avg_rating=Decimal("4.80"),
        total_earned=Decimal("1500.000000"),
    )
    assert updated is not None
    assert updated.total_jobs == 42
    assert float(updated.success_rate) == pytest.approx(95.50, abs=0.01)
    assert float(updated.avg_rating) == pytest.approx(4.80, abs=0.01)


async def test_update_stats_no_kwargs_returns_agent(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    result = await AgentRepository(db_session).update_stats(agent.id)
    assert result is not None
    assert result.id == agent.id


async def test_update_stats_unknown_returns_none(db_session: AsyncSession) -> None:
    result = await AgentRepository(db_session).update_stats(uuid.uuid4(), total_jobs=1)
    assert result is None


# ── base repo methods ─────────────────────────────────────────────────────────

async def test_delete_agent(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    repo = AgentRepository(db_session)
    assert await repo.delete(agent.id) is True
    assert await repo.get_by_id(agent.id) is None


import pytest
