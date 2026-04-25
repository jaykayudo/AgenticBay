"""
Tests for OrchestratorAgent._handle_service_request (SERVICE_AGENT message).

Covers:
  - No connected agent → ERROR(state_error)
  - Service WebSocket not open → ERROR(state_error)
  - Happy path: command + arguments forwarded verbatim to service WS
  - No message sent back to user on a successful forward
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
    make_state,
)
from app.agents.orchestrator.schema import SessionPhase

pytestmark = [pytest.mark.asyncio]


def _raw_service(command: str, arguments: dict | None = None) -> str:
    return json.dumps({
        "type": "SERVICE_AGENT",
        "data": {"command": command, "arguments": arguments or {}},
    })


# ── Guard: no connected agent ─────────────────────────────────────────────────


async def test_service_request_without_connected_agent_returns_state_error() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.STARTED)  # connected_agent_id is None
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    await orch.handle_message(state.session_id, _raw_service("RUN"), send)

    errors = send.of_type("ERROR")
    assert len(errors) == 1
    assert errors[0]["data"]["error_type"] == "state_error"
    assert "CONNECT_AGENT" in errors[0]["data"]["message"]


# ── Guard: service WS not connected ──────────────────────────────────────────


async def test_service_request_with_ws_not_connected_returns_state_error() -> None:
    store = FakeSessionStore()
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = False

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_message(state.session_id, _raw_service("RUN"), send)

    errors = send.of_type("ERROR")
    assert errors[0]["data"]["error_type"] == "state_error"


# ── Happy path ────────────────────────────────────────────────────────────────


async def test_service_request_forwards_command_to_service_ws() -> None:
    store = FakeSessionStore()
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True
    mock_manager.send_to_service = AsyncMock()

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_message(
            state.session_id,
            _raw_service("ANALYZE", {"target": "data.csv"}),
            send,
        )

    mock_manager.send_to_service.assert_called_once()


async def test_service_request_forwards_command_name_unchanged() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE, connected_agent_id=str(uuid.uuid4()))
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True
    mock_manager.send_to_service = AsyncMock()

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_message(
            state.session_id,
            _raw_service("MY_CUSTOM_CMD", {"x": 1}),
            send,
        )

    forwarded = json.loads(mock_manager.send_to_service.call_args[0][1])
    assert forwarded["command"] == "MY_CUSTOM_CMD"


async def test_service_request_forwards_arguments_unchanged() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE, connected_agent_id=str(uuid.uuid4()))
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True
    mock_manager.send_to_service = AsyncMock()

    args = {"file": "report.pdf", "pages": 10, "options": {"ocr": True}}
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_message(
            state.session_id,
            _raw_service("PROCESS", args),
            send,
        )

    forwarded = json.loads(mock_manager.send_to_service.call_args[0][1])
    assert forwarded["arguments"] == args


async def test_service_request_sends_to_correct_session() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE, connected_agent_id=str(uuid.uuid4()))
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True
    mock_manager.send_to_service = AsyncMock()

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_message(state.session_id, _raw_service("CMD"), send)

    call_session_id = mock_manager.send_to_service.call_args[0][0]
    assert call_session_id == state.session_id


async def test_service_request_sends_no_message_back_to_user() -> None:
    """Forwarding a command should not echo anything to the caller."""
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE, connected_agent_id=str(uuid.uuid4()))
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True
    mock_manager.send_to_service = AsyncMock()

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_message(state.session_id, _raw_service("RUN"), send)

    assert len(send.sent) == 0


async def test_service_request_empty_arguments_forwarded_as_empty_dict() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE, connected_agent_id=str(uuid.uuid4()))
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True
    mock_manager.send_to_service = AsyncMock()

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        raw = json.dumps({"type": "SERVICE_AGENT", "data": {"command": "START"}})
        await orch.handle_message(state.session_id, raw, send)

    forwarded = json.loads(mock_manager.send_to_service.call_args[0][1])
    assert forwarded["arguments"] == {}
