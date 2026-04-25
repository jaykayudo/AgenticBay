"""
Tests for OrchestratorAgent._handle_connect (CONNECT_AGENT message).

Covers:
  - Happy path: agent fetched → capabilities fetched → job created →
    HTTP /connect handshake → ConnectResponse
  - All session state fields updated correctly
  - Phase transitions: CONNECTING then ACTIVE
  - Agent not found → ERROR(not_found_error)
  - Capabilities fetch fails → ERROR(connect_error)
  - HTTP /connect handshake fails → ERROR(connect_error)
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.test_orchestrator_agent.conftest import (
    FakeSend,
    FakeSessionStore,
    build_orchestrator,
    make_db_agent,
    make_state,
)
from app.agents.orchestrator.schema import SessionPhase

pytestmark = [pytest.mark.asyncio]


def _raw_connect(agent_id: str) -> str:
    return json.dumps({"type": "CONNECT_AGENT", "data": {"agent_id": agent_id}})


def _wired_orch(store: FakeSessionStore, db_agent=None, caps="capability doc", connected=True):
    """Return an orchestrator with HTTP helpers already patched on the instance."""
    orch = build_orchestrator(store)
    orch._get_agent_from_db = AsyncMock(return_value=db_agent or make_db_agent())
    orch._fetch_capabilities = AsyncMock(return_value=caps)
    orch._send_connect_request = AsyncMock(return_value=connected)
    orch._create_job_in_db = AsyncMock(return_value=str(uuid.uuid4()))
    return orch


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_connect_sends_connect_response() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    agent_id = str(uuid.uuid4())
    orch = _wired_orch(store, make_db_agent(), caps="my capability doc")
    send = FakeSend()

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch.handle_message(state.session_id, _raw_connect(agent_id), send)

    connects = send.of_type("CONNECT")
    assert len(connects) == 1
    assert connects[0]["data"]["capabilities"] == "my capability doc"


async def test_connect_response_includes_agent_id() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    agent_id = str(uuid.uuid4())
    orch = _wired_orch(store)
    send = FakeSend()

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch.handle_message(state.session_id, _raw_connect(agent_id), send)

    assert send.of_type("CONNECT")[0]["data"]["agent_id"] == agent_id


async def test_connect_response_includes_next_suggested_command() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = _wired_orch(store)
    send = FakeSend()

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch.handle_message(state.session_id, _raw_connect(str(uuid.uuid4())), send)

    assert send.of_type("CONNECT")[0]["data"]["next_suggested_command"] == "SERVICE_AGENT"


# ── State persistence ─────────────────────────────────────────────────────────


async def test_connect_stores_agent_endpoint_and_wallet() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    db_agent = make_db_agent(
        base_url="https://my-agent.io",
        wallet_address="0xMY_WALLET",
        orchestrator_api_key="secret-key",
    )
    orch = _wired_orch(store, db_agent=db_agent, caps="caps")
    send = FakeSend()

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch.handle_message(state.session_id, _raw_connect(str(uuid.uuid4())), send)

    saved = await store.get(state.session_id)
    assert saved.agent_endpoint == "https://my-agent.io"
    assert saved.agent_wallet_address == "0xMY_WALLET"
    assert saved.agent_orchestrator_key == "secret-key"
    assert saved.agent_capabilities == "caps"


async def test_connect_sets_job_id_in_state() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    expected_job_id = str(uuid.uuid4())
    orch = _wired_orch(store)
    orch._create_job_in_db = AsyncMock(return_value=expected_job_id)
    send = FakeSend()

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch.handle_message(state.session_id, _raw_connect(str(uuid.uuid4())), send)

    saved = await store.get(state.session_id)
    assert saved.job_id == expected_job_id


async def test_connect_creates_job_with_correct_agent_id() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    agent_id = str(uuid.uuid4())
    orch = _wired_orch(store)
    send = FakeSend()

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch.handle_message(state.session_id, _raw_connect(agent_id), send)

    call_args = orch._create_job_in_db.call_args
    # create_job is called with (session_id, user_id, agent_id)
    assert call_args.args[2] == agent_id or call_args.kwargs.get("agent_id") == agent_id


# ── Phase transitions ─────────────────────────────────────────────────────────


async def test_connect_transitions_through_connecting_to_active() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    phases_seen: list[SessionPhase] = []

    original_save = store.save

    async def tracking_save(s):
        phases_seen.append(s.phase)
        await original_save(s)

    store.save = tracking_save  # type: ignore[method-assign]

    orch = _wired_orch(store)
    send = FakeSend()

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch.handle_message(state.session_id, _raw_connect(str(uuid.uuid4())), send)

    assert SessionPhase.CONNECTING in phases_seen
    assert SessionPhase.ACTIVE in phases_seen


async def test_connect_final_phase_is_active() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = _wired_orch(store)
    send = FakeSend()

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch.handle_message(state.session_id, _raw_connect(str(uuid.uuid4())), send)

    saved = await store.get(state.session_id)
    assert saved.phase == SessionPhase.ACTIVE


# ── HTTP helpers called with correct args ─────────────────────────────────────


async def test_connect_fetches_capabilities_from_agent_base_url() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    db_agent = make_db_agent(base_url="https://specific.agent.io")
    orch = _wired_orch(store, db_agent=db_agent)
    send = FakeSend()

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch.handle_message(state.session_id, _raw_connect(str(uuid.uuid4())), send)

    orch._fetch_capabilities.assert_called_once_with("https://specific.agent.io")


async def test_connect_sends_correct_token_in_handshake() -> None:
    store = FakeSessionStore()
    state = make_state(auth_token="my-session-jwt")
    await store.save(state)
    orch = _wired_orch(store)
    send = FakeSend()

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch.handle_message(state.session_id, _raw_connect(str(uuid.uuid4())), send)

    call_kwargs = orch._send_connect_request.call_args.kwargs
    assert call_kwargs["token"] == "my-session-jwt"
    assert call_kwargs["session_id"] == state.session_id


# ── Error paths ───────────────────────────────────────────────────────────────


async def test_connect_agent_not_found_returns_not_found_error() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    orch._get_agent_from_db = AsyncMock(return_value=None)
    send = FakeSend()

    await orch.handle_message(state.session_id, _raw_connect(str(uuid.uuid4())), send)

    errors = send.of_type("ERROR")
    assert len(errors) == 1
    assert errors[0]["data"]["error_type"] == "not_found_error"


async def test_connect_capabilities_fetch_fails_returns_connect_error() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    orch._get_agent_from_db = AsyncMock(return_value=make_db_agent())
    orch._fetch_capabilities = AsyncMock(return_value=None)
    send = FakeSend()

    await orch.handle_message(state.session_id, _raw_connect(str(uuid.uuid4())), send)

    errors = send.of_type("ERROR")
    assert errors[0]["data"]["error_type"] == "connect_error"


async def test_connect_http_handshake_failure_returns_connect_error() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    orch._get_agent_from_db = AsyncMock(return_value=make_db_agent())
    orch._fetch_capabilities = AsyncMock(return_value="caps")
    orch._send_connect_request = AsyncMock(return_value=False)
    orch._create_job_in_db = AsyncMock(return_value=str(uuid.uuid4()))
    send = FakeSend()

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch.handle_message(state.session_id, _raw_connect(str(uuid.uuid4())), send)

    errors = send.of_type("ERROR")
    assert errors[0]["data"]["error_type"] == "connect_error"


async def test_connect_no_response_sent_on_agent_not_found() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    orch._get_agent_from_db = AsyncMock(return_value=None)
    send = FakeSend()

    await orch.handle_message(state.session_id, _raw_connect(str(uuid.uuid4())), send)

    assert len(send.of_type("CONNECT")) == 0
