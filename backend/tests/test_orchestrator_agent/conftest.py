"""
Shared fakes, helpers and fixtures for OrchestratorAgent tests.

Design:
  - OrchestratorAgent is instantiated via __new__ to bypass __init__ so no
    real Redis / API clients are ever created.
  - FakeSessionStore replaces Redis with an in-memory dict.
  - FakeSend captures every outbound WebSocket message as a parsed dict.
  - build_orchestrator() wires all dependencies with AsyncMock / FakeSend.
  - DB helper methods (_get_agent_from_db, _create_job_in_db, …) are replaced
    on the instance so each test controls their return values.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.orchestrator.agent import OrchestratorAgent
from app.agents.orchestrator.schema import JobSessionState, SessionPhase
from app.services.health_client import HealthCheckResult

# ── Outbound message collector ────────────────────────────────────────────────


class FakeSend:
    """Async callable that captures all text sent to the user WebSocket."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def __call__(self, text: str) -> None:
        self.sent.append(json.loads(text))

    def of_type(self, msg_type: str) -> list[dict[str, Any]]:
        return [m for m in self.sent if m.get("type") == msg_type]

    @property
    def last(self) -> dict[str, Any] | None:
        return self.sent[-1] if self.sent else None


# ── In-memory session store ───────────────────────────────────────────────────


class FakeSessionStore:
    """Drop-in for SessionStore — no Redis, pure dict."""

    def __init__(self) -> None:
        self._store: dict[str, JobSessionState] = {}

    async def save(self, state: JobSessionState) -> None:
        self._store[state.session_id] = state.model_copy(deep=True)

    async def get(self, session_id: str) -> JobSessionState | None:
        s = self._store.get(session_id)
        return s.model_copy(deep=True) if s else None

    async def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)


# ── Factories ─────────────────────────────────────────────────────────────────


def make_state(**overrides: Any) -> JobSessionState:
    """Build a JobSessionState with safe defaults for tests."""
    defaults: dict[str, Any] = {
        "session_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "phase": SessionPhase.STARTED,
        "auth_token": "test-jwt-token",
        "created_at": datetime.now(UTC).isoformat(),
        "last_activity_at": datetime.now(UTC).isoformat(),
    }
    defaults.update(overrides)
    return JobSessionState(**defaults)


def make_db_agent(**overrides: Any) -> MagicMock:
    """Fake Agent ORM record."""
    from app.models.agents import Agent

    agent = MagicMock(spec=Agent)
    agent.id = str(uuid.uuid4())
    agent.name = "Test Agent"
    agent.base_url = "https://agent.example.com"
    agent.wallet_address = "0xAGENT_WALLET"
    agent.orchestrator_api_key = "orch-key-abc123"
    agent.pricing_summary = {}
    for k, v in overrides.items():
        setattr(agent, k, v)
    return agent


def build_orchestrator(store: FakeSessionStore | None = None) -> OrchestratorAgent:
    """
    Create OrchestratorAgent with __new__ (no __init__) so no real
    Redis / LLM / Circle clients are constructed.  All deps are AsyncMock.
    DB helper methods are also replaced so each test can configure them.
    """
    orch = OrchestratorAgent.__new__(OrchestratorAgent)
    orch.session_store = store or FakeSessionStore()
    orch.llm = AsyncMock()
    orch.vector_search = AsyncMock()
    orch.invoice_svc = AsyncMock()
    orch.http_timeout = None  # aiohttp timeout; not needed for mocked HTTP
    orch._health_client = AsyncMock()
    orch._health_client.check.return_value = HealthCheckResult(
        healthy=True,
        ready=True,
        status="ok",
        reason=None,
        agent_version="test",
        active_sessions=0,
        response_time_ms=1.0,
    )
    orch._health_client.set_cached.return_value = None

    # Internal DB helpers
    orch._get_agent_from_db = AsyncMock(return_value=None)
    orch._create_job_in_db = AsyncMock(return_value=str(uuid.uuid4()))
    orch._mark_job_completed = AsyncMock()
    orch._get_user_wallet_address = AsyncMock(return_value="0xUSER_WALLET")

    return orch


# ── pytest fixtures ───────────────────────────────────────────────────────────


@pytest.fixture
def store() -> FakeSessionStore:
    return FakeSessionStore()


@pytest.fixture
def send() -> FakeSend:
    return FakeSend()


@pytest.fixture
def orch(store: FakeSessionStore) -> OrchestratorAgent:
    return build_orchestrator(store)
