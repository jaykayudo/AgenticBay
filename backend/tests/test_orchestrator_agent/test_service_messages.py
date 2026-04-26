"""
Tests for OrchestratorAgent.handle_service_message.

This is the entry point for WebSocket messages coming FROM the service agent.
The orchestrator must parse the message type and route accordingly:

  PROGRESS   → forward progress update to user as SERVICE_AGENT message
  PAYMENT    → create invoice and send PaymentResponse to user
  JOB_DONE   → send CloseAppealResponse to user, transition to CLOSING
  generic    → forward data to user as SERVICE_AGENT message
  invalid JSON / unknown session → log and return silently (no crash)
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.orchestrator.schema import SessionPhase
from tests.test_orchestrator_agent.conftest import (
    FakeSessionStore,
    build_orchestrator,
    make_state,
)

pytestmark = [pytest.mark.asyncio]


# ── PROGRESS ──────────────────────────────────────────────────────────────────


async def test_progress_message_forwarded_as_service_agent_to_user() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE)
    await store.save(state)
    orch = build_orchestrator(store)

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    msg = json.dumps({"type": "PROGRESS", "data": {"progress": 50, "message": "halfway"}})
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_service_message(state.session_id, msg)

    mock_manager.send_to_user.assert_called_once()
    sent = json.loads(mock_manager.send_to_user.call_args[0][1])
    assert sent["type"] == "SERVICE_AGENT"
    assert sent["data"]["progress"] == 50


async def test_progress_message_includes_message_text() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE)
    await store.save(state)
    orch = build_orchestrator(store)

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    msg = json.dumps({"type": "PROGRESS", "data": {"progress": 75, "message": "almost done"}})
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_service_message(state.session_id, msg)

    sent = json.loads(mock_manager.send_to_user.call_args[0][1])
    assert sent["message"] == "almost done"


async def test_progress_message_does_not_mutate_session_state() -> None:
    """PROGRESS is fire-and-forward; no state transition should occur."""
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE)
    await store.save(state)
    orch = build_orchestrator(store)

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    msg = json.dumps({"type": "PROGRESS", "data": {"progress": 10}})
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_service_message(state.session_id, msg)

    saved = await store.get(state.session_id)
    assert saved.phase == SessionPhase.ACTIVE  # unchanged


# ── PAYMENT ───────────────────────────────────────────────────────────────────


async def test_payment_message_creates_invoice_and_sends_payment_response() -> None:
    store = FakeSessionStore()
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        agent_wallet_address="0xAGENT",
    )
    await store.save(state)
    orch = build_orchestrator(store)

    invoice = MagicMock()
    invoice.id = uuid.uuid4()
    wallet = MagicMock()
    wallet.wallet_address = "0xESCROW"
    orch.invoice_svc.create_invoice = AsyncMock(return_value=(invoice, wallet))

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    msg = json.dumps(
        {
            "type": "PAYMENT",
            "data": {"amount": "20.0", "description": "job charge", "address": None},
        }
    )
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_service_message(state.session_id, msg)

    orch.invoice_svc.create_invoice.assert_called_once()
    sent = json.loads(mock_manager.send_to_user.call_args[0][1])
    assert sent["type"] == "PAYMENT"


async def test_payment_message_sent_to_correct_session() -> None:
    store = FakeSessionStore()
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        agent_wallet_address="0xAGENT",
    )
    await store.save(state)
    orch = build_orchestrator(store)

    invoice = MagicMock()
    invoice.id = uuid.uuid4()
    wallet = MagicMock()
    wallet.wallet_address = "0xESCROW"
    orch.invoice_svc.create_invoice = AsyncMock(return_value=(invoice, wallet))

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    msg = json.dumps(
        {
            "type": "PAYMENT",
            "data": {"amount": "5.0", "description": "fee", "address": None},
        }
    )
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_service_message(state.session_id, msg)

    call_session_id = mock_manager.send_to_user.call_args[0][0]
    assert call_session_id == state.session_id


# ── JOB_DONE ──────────────────────────────────────────────────────────────────


async def test_job_done_sends_close_appeal_to_user() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE)
    await store.save(state)
    orch = build_orchestrator(store)

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    msg = json.dumps(
        {
            "type": "JOB_DONE",
            "data": {"message": "Task complete!", "details": {"output": "result.csv"}},
        }
    )
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_service_message(state.session_id, msg)

    mock_manager.send_to_user.assert_called_once()
    sent = json.loads(mock_manager.send_to_user.call_args[0][1])
    assert sent["type"] == "CLOSE_APPEAL"


async def test_job_done_includes_message_and_details() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE)
    await store.save(state)
    orch = build_orchestrator(store)

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    msg = json.dumps(
        {
            "type": "JOB_DONE",
            "data": {"message": "Done!", "details": {"rows": 42}},
        }
    )
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_service_message(state.session_id, msg)

    sent = json.loads(mock_manager.send_to_user.call_args[0][1])
    assert sent["data"]["message"] == "Done!"
    assert sent["data"]["details"] == {"rows": 42}


async def test_job_done_transitions_phase_to_closing() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE)
    await store.save(state)
    orch = build_orchestrator(store)

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    msg = json.dumps({"type": "JOB_DONE", "data": {"message": "done", "details": {}}})
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_service_message(state.session_id, msg)

    saved = await store.get(state.session_id)
    assert saved.phase == SessionPhase.CLOSING


async def test_job_done_includes_next_suggested_command() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE)
    await store.save(state)
    orch = build_orchestrator(store)

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    msg = json.dumps({"type": "JOB_DONE", "data": {"message": "done", "details": {}}})
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_service_message(state.session_id, msg)

    sent = json.loads(mock_manager.send_to_user.call_args[0][1])
    assert sent.get("next_suggested_command") == "CLOSE"


# ── Generic response ──────────────────────────────────────────────────────────


async def test_generic_message_forwarded_as_service_agent_to_user() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE)
    await store.save(state)
    orch = build_orchestrator(store)

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    msg = json.dumps({"data": {"result": "some structured output", "count": 5}})
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_service_message(state.session_id, msg)

    mock_manager.send_to_user.assert_called_once()
    sent = json.loads(mock_manager.send_to_user.call_args[0][1])
    assert sent["type"] == "SERVICE_AGENT"


# ── Error resilience ──────────────────────────────────────────────────────────


async def test_invalid_json_does_not_raise() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE)
    await store.save(state)
    orch = build_orchestrator(store)

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        # Must not raise
        await orch.handle_service_message(state.session_id, "not json {{{")

    mock_manager.send_to_user.assert_not_called()


async def test_session_not_found_does_not_raise() -> None:
    store = FakeSessionStore()  # empty
    orch = build_orchestrator(store)

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_service_message(
            "nonexistent-session-id",
            '{"type": "PROGRESS", "data": {"progress": 10}}',
        )

    mock_manager.send_to_user.assert_not_called()


async def test_typeless_message_with_data_handled_as_generic() -> None:
    """A message with no 'type' but a valid 'data' field is forwarded as generic."""
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE)
    await store.save(state)
    orch = build_orchestrator(store)

    mock_manager = MagicMock()
    mock_manager.send_to_user = AsyncMock()

    msg = json.dumps({"data": {"output": "analysis complete", "rows": 100}})
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_service_message(state.session_id, msg)

    mock_manager.send_to_user.assert_called_once()
    sent = json.loads(mock_manager.send_to_user.call_args[0][1])
    assert sent["type"] == "SERVICE_AGENT"
