"""
Tests for the background health check task:
  - Redis cache correctly stores health status
  - Consecutive failure counting
  - Auto-suspension after 5 failures
  - Search filters out unhealthy agents from results
  - Pre-connect health check blocks connection to unhealthy agents
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.health_client import AgentHealthClient, HealthCheckResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def _healthy_result(**kw) -> HealthCheckResult:
    return HealthCheckResult(
        healthy=True, ready=True, status="ok",
        reason=None, agent_version="1.0.0",
        active_sessions=0, response_time_ms=50.0, **kw,
    )


def _unhealthy_result(reason: str = "Connection refused") -> HealthCheckResult:
    return HealthCheckResult(
        healthy=False, ready=False, status="unreachable",
        reason=reason, agent_version=None,
        active_sessions=None, response_time_ms=3000.0,
    )


# ── Redis cache tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_cached_stores_correct_structure() -> None:
    agent_id = str(uuid.uuid4())
    result = _healthy_result()
    fake_redis = AsyncMock()

    with patch("app.services.health_client.get_redis", return_value=fake_redis):
        await AgentHealthClient().set_cached(agent_id, result, 0)

    fake_redis.set.assert_called_once()
    call_args = fake_redis.set.call_args
    key = call_args[0][0]
    payload_str = call_args[0][1]

    import json
    payload = json.loads(payload_str)

    assert f"agent_health:{agent_id}" == key
    assert payload["healthy"] is True
    assert payload["ready"] is True
    assert payload["status"] == "ok"
    assert payload["consecutive_failures"] == 0
    assert payload["agent_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_get_cached_returns_none_on_miss() -> None:
    fake_redis = AsyncMock()
    fake_redis.get.return_value = None

    with patch("app.services.health_client.get_redis", return_value=fake_redis):
        result = await AgentHealthClient().get_cached("no-such-agent")

    assert result is None


@pytest.mark.asyncio
async def test_is_healthy_from_cache_returns_none_on_miss() -> None:
    fake_redis = AsyncMock()
    fake_redis.get.return_value = None

    with patch("app.services.health_client.get_redis", return_value=fake_redis):
        result = await AgentHealthClient().is_healthy_from_cache("no-such-agent")

    assert result is None


@pytest.mark.asyncio
async def test_is_healthy_from_cache_returns_false_for_unhealthy() -> None:
    import json
    cached = json.dumps({"healthy": False, "ready": False, "status": "unreachable"})
    fake_redis = AsyncMock()
    fake_redis.get.return_value = cached

    with patch("app.services.health_client.get_redis", return_value=fake_redis):
        result = await AgentHealthClient().is_healthy_from_cache("agent-123")

    assert result is False


@pytest.mark.asyncio
async def test_is_healthy_from_cache_returns_true_for_healthy() -> None:
    import json
    cached = json.dumps({"healthy": True, "ready": True, "status": "ok"})
    fake_redis = AsyncMock()
    fake_redis.get.return_value = cached

    with patch("app.services.health_client.get_redis", return_value=fake_redis):
        result = await AgentHealthClient().is_healthy_from_cache("agent-abc")

    assert result is True


# ── Consecutive failure counting ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_and_persist_increments_failures_on_unhealthy() -> None:
    from app.tasks.agent_health_tasks import _check_and_persist

    agent_id = uuid.uuid4()
    owner_id = uuid.uuid4()
    base_url = "http://agent.local"

    mock_agent = MagicMock()
    mock_agent.status.value = "ACTIVE"
    mock_agent.consecutive_health_failures = 2  # already had 2 failures

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = mock_agent
    mock_repo.update_health_status = AsyncMock()
    mock_repo.update = AsyncMock()

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    with (
        patch("app.tasks.agent_health_tasks.AgentHealthClient") as mock_client_cls,
        patch("app.tasks.agent_health_tasks.AsyncSessionLocal") as mock_session_cls,
        patch("app.tasks.agent_health_tasks.AgentRepository", return_value=mock_repo),
    ):
        mock_client = AsyncMock()
        mock_client.check = AsyncMock(return_value=_unhealthy_result())
        mock_client.set_cached = AsyncMock()
        mock_client_cls.return_value = mock_client

        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _check_and_persist(agent_id, base_url, owner_id)

    # Should have been called with consecutive_failures=3
    mock_repo.update_health_status.assert_called_once()
    call_kwargs = mock_repo.update_health_status.call_args[1]
    assert call_kwargs["consecutive_failures"] == 3


@pytest.mark.asyncio
async def test_check_and_persist_resets_failures_on_healthy() -> None:
    from app.tasks.agent_health_tasks import _check_and_persist

    agent_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    mock_agent = MagicMock()
    mock_agent.consecutive_health_failures = 3

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = mock_agent
    mock_repo.update_health_status = AsyncMock()

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    with (
        patch("app.tasks.agent_health_tasks.AgentHealthClient") as mock_client_cls,
        patch("app.tasks.agent_health_tasks.AsyncSessionLocal") as mock_session_cls,
        patch("app.tasks.agent_health_tasks.AgentRepository", return_value=mock_repo),
    ):
        mock_client = AsyncMock()
        mock_client.check = AsyncMock(return_value=_healthy_result())
        mock_client.set_cached = AsyncMock()
        mock_client_cls.return_value = mock_client

        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _check_and_persist(agent_id, "http://agent.local", owner_id)

    call_kwargs = mock_repo.update_health_status.call_args[1]
    assert call_kwargs["consecutive_failures"] == 0


# ── Auto-suspension test ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auto_suspend_triggers_after_five_failures() -> None:
    from app.tasks.agent_health_tasks import _check_and_persist

    agent_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    mock_agent = MagicMock()
    mock_agent.consecutive_health_failures = 4  # next failure = 5 → suspend

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = mock_agent
    mock_repo.update_health_status = AsyncMock()

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()

    with (
        patch("app.tasks.agent_health_tasks.AgentHealthClient") as mock_client_cls,
        patch("app.tasks.agent_health_tasks.AsyncSessionLocal") as mock_session_cls,
        patch("app.tasks.agent_health_tasks.AgentRepository", return_value=mock_repo),
        patch("app.tasks.agent_health_tasks._suspend_agent") as mock_suspend,
        patch("app.tasks.agent_health_tasks._notify_owner") as mock_notify,
    ):
        mock_client = AsyncMock()
        mock_client.check = AsyncMock(return_value=_unhealthy_result())
        mock_client.set_cached = AsyncMock()
        mock_client_cls.return_value = mock_client

        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_suspend = AsyncMock()
        mock_notify = AsyncMock()

        with patch("app.tasks.agent_health_tasks._suspend_agent", mock_suspend):
            await _check_and_persist(agent_id, "http://agent.local", owner_id)

    mock_suspend.assert_called_once_with(
        agent_id, "http://agent.local", owner_id, 5, "Connection refused"
    )


# ── Search health filter tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vector_search_filters_unhealthy_agents() -> None:
    from app.agents.orchestrator.vector_search import VectorSearch

    vs = VectorSearch()

    agents = [
        {"id": "agent-healthy", "name": "Good Agent", "base_url": "http://good.local"},
        {"id": "agent-unhealthy", "name": "Bad Agent", "base_url": "http://bad.local"},
    ]

    async def fake_is_healthy(agent_id: str) -> bool | None:
        return agent_id == "agent-healthy"

    with patch.object(vs._health_client, "is_healthy_from_cache", side_effect=fake_is_healthy):
        result = await vs._filter_healthy(agents)

    assert len(result) == 1
    assert result[0]["id"] == "agent-healthy"


@pytest.mark.asyncio
async def test_vector_search_live_checks_uncached_agents() -> None:
    from app.agents.orchestrator.vector_search import VectorSearch

    vs = VectorSearch()
    agents = [{"id": "new-agent", "name": "New", "base_url": "http://new.local"}]

    # Cache miss → live check → healthy
    with (
        patch.object(vs._health_client, "is_healthy_from_cache", return_value=None),
        patch.object(vs._health_client, "check", return_value=_healthy_result()),
        patch.object(vs._health_client, "set_cached", return_value=None),
    ):
        result = await vs._filter_healthy(agents)

    assert len(result) == 1


@pytest.mark.asyncio
async def test_vector_search_excludes_live_checked_unhealthy() -> None:
    from app.agents.orchestrator.vector_search import VectorSearch

    vs = VectorSearch()
    agents = [{"id": "down-agent", "name": "Down", "base_url": "http://down.local"}]

    with (
        patch.object(vs._health_client, "is_healthy_from_cache", return_value=None),
        patch.object(vs._health_client, "check", return_value=_unhealthy_result()),
        patch.object(vs._health_client, "set_cached"),
    ):
        result = await vs._filter_healthy(agents)

    assert len(result) == 0


# ── Pre-connect health check ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pre_connect_blocks_unhealthy_agent() -> None:
    """OrchestratorAgent._handle_connect sends error if health check fails."""
    from app.agents.orchestrator.agent import OrchestratorAgent
    from app.agents.orchestrator.schema import ConnectAgentRequest, ConnectAgentRequestData, JobSessionState, SessionPhase

    orchestrator = OrchestratorAgent()

    state = JobSessionState(
        session_id="sess-1",
        user_id="user-1",
        phase=SessionPhase.STARTED,
        auth_token="tok",
        created_at="2026-04-25T00:00:00",
        last_activity_at="2026-04-25T00:00:00",
    )

    message = ConnectAgentRequest(
        type="CONNECT_AGENT",
        data=ConnectAgentRequestData(agent_id="agent-123"),
    )

    mock_agent = MagicMock()
    mock_agent.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    mock_agent.base_url = "http://agent.local"
    mock_agent.wallet_address = "0xABC"
    mock_agent.orchestrator_api_key = "key-123"

    sent: list[str] = []

    async def fake_send(text: str) -> None:
        sent.append(text)

    with (
        patch.object(orchestrator, "_get_agent_from_db", return_value=mock_agent),
        patch.object(orchestrator._health_client, "check", return_value=_unhealthy_result()),
        patch.object(orchestrator._health_client, "set_cached"),
        patch.object(orchestrator.session_store, "save"),
    ):
        await orchestrator._handle_connect(state, message, fake_send)

    import json
    assert len(sent) == 1
    response = json.loads(sent[0])
    assert response["type"] == "ERROR"
    assert response["data"]["error_type"] == "agent_unavailable"
