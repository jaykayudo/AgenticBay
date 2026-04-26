"""
Tests for the full payment pipeline inside OrchestratorAgent.

Three sub-flows tested here:

1. _handle_payment_request  (triggered when service agent sends PAYMENT)
   - Creates invoice, assigns escrow wallet, responds with PaymentResponse
   - Guards: no job_id, no payee address, invoice creation failure

2. _handle_payment_successful (PAYMENT_SUCCESSFUL from user)
   - Confirms payment with InvoiceService
   - Updates state (phase → ACTIVE, invoice added to paid list)
   - Notifies service agent via LLM-resolved command
   - Guard: confirmation fails → ERROR(payment_error)

3. _handle_close (CLOSE from user)
   - Calls disburse when there are paid invoices
   - Notifies service agent with PAYMENT_TRANSFERRED if WS is open
   - Marks job completed
   - Works correctly even when there are no paid invoices
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.orchestrator.schema import (
    ServicePaymentRequest,
    ServicePaymentRequestData,
    SessionPhase,
)
from tests.test_orchestrator_agent.conftest import (
    FakeSend,
    FakeSessionStore,
    build_orchestrator,
    make_state,
)

pytestmark = [pytest.mark.asyncio]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_invoice_mock(invoice_id: str | None = None) -> MagicMock:
    from app.models.invoices import Invoice

    inv = MagicMock(spec=Invoice)
    inv.id = uuid.UUID(invoice_id) if invoice_id else uuid.uuid4()
    return inv


def _make_wallet_mock(address: str = "0xESCROW_WALLET") -> MagicMock:
    from app.models.wallets import EscrowWallet

    w = MagicMock(spec=EscrowWallet)
    w.id = uuid.uuid4()
    w.wallet_address = address
    return w


def _payment_request(
    amount: str = "25.0", description: str = "job fee", address: str | None = None
) -> ServicePaymentRequest:
    return ServicePaymentRequest(
        type="PAYMENT",
        data=ServicePaymentRequestData(amount=amount, description=description, address=address),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PAYMENT REQUEST (service → orchestrator → user)
# ═══════════════════════════════════════════════════════════════════════════════


async def test_payment_request_sends_payment_response() -> None:
    store = FakeSessionStore()
    invoice_id = str(uuid.uuid4())
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        agent_wallet_address="0xAGENT",
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    invoice = _make_invoice_mock(invoice_id)
    wallet = _make_wallet_mock("0xESCROW")
    orch.invoice_svc.create_invoice = AsyncMock(return_value=(invoice, wallet))

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch._handle_payment_request(state, _payment_request("25.0", "Analysis"), send)

    payments = send.of_type("PAYMENT")
    assert len(payments) == 1
    assert payments[0]["data"]["amount"] == 25.0
    assert payments[0]["data"]["description"] == "Analysis"


async def test_payment_request_response_contains_invoice_details() -> None:
    store = FakeSessionStore()
    invoice_id = str(uuid.uuid4())
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        agent_wallet_address="0xAGENT",
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    invoice = _make_invoice_mock(invoice_id)
    wallet = _make_wallet_mock("0xESCROW_ADDR")
    orch.invoice_svc.create_invoice = AsyncMock(return_value=(invoice, wallet))

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch._handle_payment_request(state, _payment_request(), send)

    payment_info = send.of_type("PAYMENT")[0]["data"]["payment_info"]
    assert payment_info["invoice_id"] == str(invoice.id)
    assert payment_info["invoice_wallet"] == "0xESCROW_ADDR"
    assert "blockchain" in payment_info


async def test_payment_request_sets_phase_to_awaiting_payment() -> None:
    store = FakeSessionStore()
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        agent_wallet_address="0xAGENT",
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.create_invoice = AsyncMock(
        return_value=(_make_invoice_mock(), _make_wallet_mock())
    )

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch._handle_payment_request(state, _payment_request(), send)

    saved = await store.get(state.session_id)
    assert saved.phase == SessionPhase.AWAITING_PAYMENT


async def test_payment_request_stores_pending_invoice_id() -> None:
    store = FakeSessionStore()
    invoice_id = str(uuid.uuid4())
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        agent_wallet_address="0xAGENT",
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    invoice = _make_invoice_mock(invoice_id)
    orch.invoice_svc.create_invoice = AsyncMock(return_value=(invoice, _make_wallet_mock()))

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch._handle_payment_request(state, _payment_request(), send)

    saved = await store.get(state.session_id)
    assert saved.pending_invoice_id == str(invoice.id)


async def test_payment_request_passes_service_address_when_provided() -> None:
    """Service agent's explicit address must be used over the stored state wallet."""
    store = FakeSessionStore()
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        agent_wallet_address="0xSTATE_WALLET",  # should NOT be used
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.create_invoice = AsyncMock(
        return_value=(_make_invoice_mock(), _make_wallet_mock())
    )

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch._handle_payment_request(
            state, _payment_request(address="0xSERVICE_WALLET"), send
        )

    call_kwargs = orch.invoice_svc.create_invoice.call_args.kwargs
    assert call_kwargs["payee_wallet_address"] == "0xSERVICE_WALLET"


async def test_payment_request_falls_back_to_state_wallet_when_no_service_address() -> None:
    store = FakeSessionStore()
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        agent_wallet_address="0xSTATE_WALLET",
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.create_invoice = AsyncMock(
        return_value=(_make_invoice_mock(), _make_wallet_mock())
    )

    # No address in the service payment → falls back to state.agent_wallet_address
    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch._handle_payment_request(state, _payment_request(address=None), send)

    call_kwargs = orch.invoice_svc.create_invoice.call_args.kwargs
    assert call_kwargs["payee_wallet_address"] == "0xSTATE_WALLET"


async def test_payment_request_no_job_id_returns_state_error() -> None:
    store = FakeSessionStore()
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
        job_id=None,  # ← not set yet
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    await orch._handle_payment_request(state, _payment_request(), send)

    errors = send.of_type("ERROR")
    assert errors[0]["data"]["error_type"] == "state_error"


async def test_payment_request_no_payee_address_returns_payment_error() -> None:
    store = FakeSessionStore()
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        agent_wallet_address=None,  # ← not set
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    # Payment also has no address
    await orch._handle_payment_request(state, _payment_request(address=None), send)

    errors = send.of_type("ERROR")
    assert errors[0]["data"]["error_type"] == "payment_error"


async def test_payment_request_invoice_creation_exception_returns_invoice_error() -> None:
    store = FakeSessionStore()
    state = make_state(
        phase=SessionPhase.ACTIVE,
        connected_agent_id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        agent_wallet_address="0xAGENT",
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.create_invoice = AsyncMock(side_effect=RuntimeError("DB error"))

    with patch("app.agents.orchestrator.agent.session_manager"):
        await orch._handle_payment_request(state, _payment_request(), send)

    errors = send.of_type("ERROR")
    assert errors[0]["data"]["error_type"] == "invoice_error"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PAYMENT_SUCCESSFUL (user → orchestrator)
# ═══════════════════════════════════════════════════════════════════════════════


async def test_payment_successful_sends_confirmation_to_user() -> None:
    store = FakeSessionStore()
    invoice_id = str(uuid.uuid4())
    state = make_state(
        phase=SessionPhase.AWAITING_PAYMENT,
        connected_agent_id=str(uuid.uuid4()),
        agent_capabilities="caps",
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.confirm_payment = AsyncMock(return_value=True)
    orch.llm.find_payment_success_command = AsyncMock(
        return_value={"command": "PAYMENT_SUCCESSFUL", "arguments_template": {}}
    )

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True
    mock_manager.send_to_service = AsyncMock()

    raw = json.dumps({"type": "PAYMENT_SUCCESSFUL", "data": {"invoice_id": invoice_id}})
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_message(state.session_id, raw, send)

    confirmations = send.of_type("PAYMENT_SUCCESSFUL")
    assert len(confirmations) == 1
    assert confirmations[0]["data"]["invoice_id"] == invoice_id


async def test_payment_successful_phase_returns_to_active() -> None:
    store = FakeSessionStore()
    invoice_id = str(uuid.uuid4())
    state = make_state(
        phase=SessionPhase.AWAITING_PAYMENT,
        connected_agent_id=str(uuid.uuid4()),
        agent_capabilities="caps",
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.confirm_payment = AsyncMock(return_value=True)
    orch.llm.find_payment_success_command = AsyncMock(
        return_value={"command": "PAYMENT_SUCCESSFUL", "arguments_template": {}}
    )

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True
    mock_manager.send_to_service = AsyncMock()

    raw = json.dumps({"type": "PAYMENT_SUCCESSFUL", "data": {"invoice_id": invoice_id}})
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_message(state.session_id, raw, send)

    saved = await store.get(state.session_id)
    assert saved.phase == SessionPhase.ACTIVE


async def test_payment_successful_adds_invoice_to_paid_list() -> None:
    store = FakeSessionStore()
    invoice_id = str(uuid.uuid4())
    state = make_state(
        phase=SessionPhase.AWAITING_PAYMENT,
        connected_agent_id=str(uuid.uuid4()),
        agent_capabilities="caps",
        pending_invoice_id=invoice_id,
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.confirm_payment = AsyncMock(return_value=True)
    orch.llm.find_payment_success_command = AsyncMock(
        return_value={"command": "PAY_CONFIRMED", "arguments_template": {}}
    )

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True
    mock_manager.send_to_service = AsyncMock()

    raw = json.dumps({"type": "PAYMENT_SUCCESSFUL", "data": {"invoice_id": invoice_id}})
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_message(state.session_id, raw, send)

    saved = await store.get(state.session_id)
    assert invoice_id in saved.paid_invoice_ids
    assert saved.pending_invoice_id is None


async def test_payment_successful_notifies_service_with_llm_resolved_command() -> None:
    store = FakeSessionStore()
    invoice_id = str(uuid.uuid4())
    state = make_state(
        phase=SessionPhase.AWAITING_PAYMENT,
        connected_agent_id=str(uuid.uuid4()),
        agent_capabilities="agent capability doc",
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.confirm_payment = AsyncMock(return_value=True)
    orch.llm.find_payment_success_command = AsyncMock(
        return_value={"command": "MY_PAYMENT_CMD", "arguments_template": {}}
    )

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True
    mock_manager.send_to_service = AsyncMock()

    raw = json.dumps({"type": "PAYMENT_SUCCESSFUL", "data": {"invoice_id": invoice_id}})
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_message(state.session_id, raw, send)

    mock_manager.send_to_service.assert_called_once()
    forwarded = json.loads(mock_manager.send_to_service.call_args[0][1])
    assert forwarded["command"] == "MY_PAYMENT_CMD"
    assert forwarded["arguments"]["invoice_id"] == invoice_id


async def test_payment_successful_llm_receives_agent_capabilities() -> None:
    store = FakeSessionStore()
    invoice_id = str(uuid.uuid4())
    expected_caps = "here are the specific capability instructions"
    state = make_state(
        phase=SessionPhase.AWAITING_PAYMENT,
        connected_agent_id=str(uuid.uuid4()),
        agent_capabilities=expected_caps,
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.confirm_payment = AsyncMock(return_value=True)
    orch.llm.find_payment_success_command = AsyncMock(
        return_value={"command": "CMD", "arguments_template": {}}
    )

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True
    mock_manager.send_to_service = AsyncMock()

    raw = json.dumps({"type": "PAYMENT_SUCCESSFUL", "data": {"invoice_id": invoice_id}})
    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        await orch.handle_message(state.session_id, raw, send)

    call_kwargs = orch.llm.find_payment_success_command.call_args.kwargs
    assert call_kwargs["capabilities"] == expected_caps


async def test_payment_successful_confirm_fails_returns_payment_error() -> None:
    store = FakeSessionStore()
    invoice_id = str(uuid.uuid4())
    state = make_state(phase=SessionPhase.AWAITING_PAYMENT)
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.confirm_payment = AsyncMock(return_value=False)

    raw = json.dumps({"type": "PAYMENT_SUCCESSFUL", "data": {"invoice_id": invoice_id}})
    await orch.handle_message(state.session_id, raw, send)

    errors = send.of_type("ERROR")
    assert errors[0]["data"]["error_type"] == "payment_error"
    assert (
        "escrow" in errors[0]["data"]["message"].lower()
        or "not yet" in errors[0]["data"]["message"].lower()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CLOSE (user → orchestrator)
# ═══════════════════════════════════════════════════════════════════════════════


async def test_close_sets_phase_to_closed() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE, paid_invoice_ids=[])
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = False

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        raw = json.dumps({"type": "CLOSE", "data": None})
        await orch.handle_message(state.session_id, raw, send)

    saved = await store.get(state.session_id)
    assert saved.phase == SessionPhase.CLOSED


async def test_close_marks_job_completed() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE, job_id=str(uuid.uuid4()))
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = False

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        raw = json.dumps({"type": "CLOSE", "data": None})
        await orch.handle_message(state.session_id, raw, send)

    orch._mark_job_completed.assert_called_once()


async def test_close_without_paid_invoices_skips_disburse() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE, paid_invoice_ids=[])
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = False

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        raw = json.dumps({"type": "CLOSE", "data": None})
        await orch.handle_message(state.session_id, raw, send)

    orch.invoice_svc.disburse_session_invoices.assert_not_called()


async def test_close_with_paid_invoices_calls_disburse() -> None:
    store = FakeSessionStore()
    invoice_id = str(uuid.uuid4())
    state = make_state(
        phase=SessionPhase.ACTIVE,
        job_id=str(uuid.uuid4()),
        paid_invoice_ids=[invoice_id],
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.disburse_session_invoices = AsyncMock(
        return_value=[{"invoice_id": invoice_id, "success": True}]
    )

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = False

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        raw = json.dumps({"type": "CLOSE", "data": None})
        await orch.handle_message(state.session_id, raw, send)

    orch.invoice_svc.disburse_session_invoices.assert_called_once_with(session_id=state.session_id)


async def test_close_notifies_service_with_payment_transferred_when_connected() -> None:
    store = FakeSessionStore()
    invoice_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    state = make_state(
        phase=SessionPhase.ACTIVE,
        job_id=str(uuid.uuid4()),
        paid_invoice_ids=invoice_ids,
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.disburse_session_invoices = AsyncMock(return_value=[])

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True
    mock_manager.send_to_service = AsyncMock()

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        raw = json.dumps({"type": "CLOSE", "data": None})
        await orch.handle_message(state.session_id, raw, send)

    mock_manager.send_to_service.assert_called_once()
    forwarded = json.loads(mock_manager.send_to_service.call_args[0][1])
    assert forwarded["command"] == "PAYMENT_TRANSFERRED"
    assert set(forwarded["arguments"]["invoice_ids"]) == set(invoice_ids)


async def test_close_does_not_notify_service_when_not_connected() -> None:
    store = FakeSessionStore()
    state = make_state(
        phase=SessionPhase.ACTIVE,
        paid_invoice_ids=[str(uuid.uuid4())],
    )
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    orch.invoice_svc.disburse_session_invoices = AsyncMock(return_value=[])

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = False
    mock_manager.send_to_service = AsyncMock()

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        raw = json.dumps({"type": "CLOSE", "data": None})
        await orch.handle_message(state.session_id, raw, send)

    mock_manager.send_to_service.assert_not_called()


async def test_close_without_paid_invoices_does_not_notify_service() -> None:
    store = FakeSessionStore()
    state = make_state(phase=SessionPhase.ACTIVE, paid_invoice_ids=[])
    await store.save(state)
    orch = build_orchestrator(store)
    send = FakeSend()

    mock_manager = MagicMock()
    mock_manager.is_service_connected.return_value = True  # connected but no invoices
    mock_manager.send_to_service = AsyncMock()

    with patch("app.agents.orchestrator.agent.session_manager", mock_manager):
        raw = json.dumps({"type": "CLOSE", "data": None})
        await orch.handle_message(state.session_id, raw, send)

    mock_manager.send_to_service.assert_not_called()
