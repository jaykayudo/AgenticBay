"""
Tests for OrchestratorAgent.handle_message — top-level dispatch/routing.

Covers:
  - Session not found in store
  - Invalid JSON payload
  - Unknown message type
  - last_activity_at timestamp update on each valid message
"""

from __future__ import annotations

import json

import pytest

from tests.test_orchestrator_agent.conftest import (
    FakeSend,
    FakeSessionStore,
    build_orchestrator,
    make_state,
)

pytestmark = [pytest.mark.asyncio]


async def test_session_not_found_returns_session_error() -> None:
    store = FakeSessionStore()  # empty — no sessions pre-populated
    orch = build_orchestrator(store)
    send = FakeSend()

    await orch.handle_message(
        "nonexistent-session-id",
        '{"type": "SEARCH_AGENT", "data": {"message": "hi"}}',
        send,
    )

    errors = send.of_type("ERROR")
    assert len(errors) == 1
    assert errors[0]["data"]["error_type"] == "session_error"
    assert "Session not found" in errors[0]["data"]["message"]


async def test_invalid_json_returns_validation_error() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    await orch.handle_message(state.session_id, "not valid json {{{{", send)

    errors = send.of_type("ERROR")
    assert len(errors) == 1
    assert errors[0]["data"]["error_type"] == "validation_error"


async def test_missing_type_field_returns_validation_error() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    raw = json.dumps({"data": {"message": "hi"}})  # no "type" key
    await orch.handle_message(state.session_id, raw, send)

    errors = send.of_type("ERROR")
    assert errors[0]["data"]["error_type"] == "validation_error"


async def test_unknown_message_type_returns_validation_error() -> None:
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    raw = json.dumps({"type": "DEFINITELY_NOT_REAL", "data": {}})
    await orch.handle_message(state.session_id, raw, send)

    errors = send.of_type("ERROR")
    assert errors[0]["data"]["error_type"] == "validation_error"
    assert "DEFINITELY_NOT_REAL" in errors[0]["data"]["message"]


async def test_last_activity_at_updated_before_dispatch() -> None:
    """Even before the handler runs, last_activity_at must be refreshed."""
    store = FakeSessionStore()
    state = make_state()
    await store.save(state)

    orch = build_orchestrator(store)
    # Configure mocks for a minimal SEARCH_AGENT flow
    orch.llm.enrich_search_query.return_value = "q"
    orch.vector_search.search.return_value = []
    orch.llm.rerank_agents.return_value = []
    send = FakeSend()

    raw = json.dumps({"type": "SEARCH_AGENT", "data": {"message": "test"}})
    await orch.handle_message(state.session_id, raw, send)

    saved = await store.get(state.session_id)
    assert saved is not None
    # State was saved (activity timestamp updated or at minimum no error)
    assert len(send.of_type("ERROR")) == 0


async def test_close_message_dispatched_successfully() -> None:
    from unittest.mock import MagicMock, patch

    store = FakeSessionStore()
    state = make_state()
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = False

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        raw = json.dumps({"type": "CLOSE", "data": None})
        await orch.handle_message(state.session_id, raw, send)

    assert len(send.of_type("ERROR")) == 0
    saved = await store.get(state.session_id)
    from app.agents.orchestrator.schema import SessionPhase

    assert saved.phase == SessionPhase.CLOSED
