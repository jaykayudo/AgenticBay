"""
Unit tests for InvoiceService.

All external dependencies (Circle API, DB) are mocked so these tests
run without a live database or network.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.invoices import Invoice, InvoiceStatus
from app.models.wallets import EscrowWallet, EscrowWalletStatus

pytestmark = [pytest.mark.asyncio]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _make_invoice(**overrides: Any) -> Invoice:
    inv = MagicMock(spec=Invoice)
    inv.id = uuid.uuid4()
    inv.status = InvoiceStatus.PENDING
    inv.amount = Decimal("100.000000")
    inv.marketplace_fee = Decimal("5.000000")
    inv.agent_payout = Decimal("95.000000")
    inv.escrow_wallet_id = None
    inv.escrow_wallet = None
    inv.payer_wallet_address = "0xPAYER"
    inv.payee_wallet_address = "0xAGENT"
    for k, v in overrides.items():
        setattr(inv, k, v)
    return inv


def _make_wallet(**overrides: Any) -> EscrowWallet:
    w = MagicMock(spec=EscrowWallet)
    w.id = uuid.uuid4()
    w.circle_wallet_id = "circle-wallet-001"
    w.wallet_address = "0xESCROW"
    w.status = EscrowWalletStatus.AVAILABLE
    w.locked_invoice_id = None
    for k, v in overrides.items():
        setattr(w, k, v)
    return w


def _session_factory(mock_session: Any) -> Any:
    """Return a mock that behaves as `async with AsyncSessionLocal() as s:`."""

    @asynccontextmanager
    async def _factory():
        yield mock_session

    return _factory


@pytest.fixture
def svc():
    """InvoiceService with Circle and escrow mocked at the instance level."""
    with (
        patch("app.services.invoice_service.CircleClient"),
        patch("app.services.invoice_service.EscrowWalletService"),
    ):
        from app.services.invoice_service import InvoiceService

        instance = InvoiceService()
        instance.circle = AsyncMock()
        instance.escrow = AsyncMock()
        yield instance


# ─────────────────────────────────────────────────────────────────────────────
# Fee calculation
# ─────────────────────────────────────────────────────────────────────────────


async def test_fee_split_math() -> None:
    """5% fee on $100 → $5.00 fee, $95.00 payout."""
    fee_pct = Decimal("5") / Decimal("100")
    amount = Decimal("100.000000")
    fee = (amount * fee_pct).quantize(Decimal("0.000001"))
    payout = amount - fee
    assert fee == Decimal("5.000000")
    assert payout == Decimal("95.000000")


async def test_fee_split_fractional_amount() -> None:
    """5% fee on $33.33 rounds to 6 decimal places."""
    fee_pct = Decimal("5") / Decimal("100")
    amount = Decimal("33.330000")
    fee = (amount * fee_pct).quantize(Decimal("0.000001"))
    payout = amount - fee
    assert fee + payout == amount


# ─────────────────────────────────────────────────────────────────────────────
# create_invoice
# ─────────────────────────────────────────────────────────────────────────────


async def test_create_invoice_returns_invoice_and_wallet(svc: Any) -> None:
    mock_invoice = _make_invoice()
    mock_wallet = _make_wallet()

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_invoice)

    with (
        patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)),
        patch(
            "app.services.invoice_service.InvoiceRepository.create",
            AsyncMock(return_value=mock_invoice),
        ),
    ):
        svc.escrow.acquire_wallet = AsyncMock(return_value=mock_wallet)

        invoice, wallet = await svc.create_invoice(
            session_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            payer_user_id=str(uuid.uuid4()),
            service_agent_id=str(uuid.uuid4()),
            amount=100.0,
            description="Test job",
            payee_wallet_address="0xAGENT",
        )

    assert invoice is mock_invoice
    assert wallet is mock_wallet


async def test_create_invoice_acquires_escrow_wallet(svc: Any) -> None:
    mock_invoice = _make_invoice()
    mock_wallet = _make_wallet()
    invoice_id = str(mock_invoice.id)

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_invoice)

    with (
        patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)),
        patch(
            "app.services.invoice_service.InvoiceRepository.create",
            AsyncMock(return_value=mock_invoice),
        ),
    ):
        svc.escrow.acquire_wallet = AsyncMock(return_value=mock_wallet)

        await svc.create_invoice(
            session_id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            payer_user_id=str(uuid.uuid4()),
            service_agent_id=str(uuid.uuid4()),
            amount=50.0,
            description="Test",
            payee_wallet_address="0xAGENT",
        )

    svc.escrow.acquire_wallet.assert_called_once_with(invoice_id)


# ─────────────────────────────────────────────────────────────────────────────
# confirm_payment
# ─────────────────────────────────────────────────────────────────────────────


async def test_confirm_payment_returns_false_when_invoice_missing(svc: Any) -> None:
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)

    with patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)):
        result = await svc.confirm_payment(str(uuid.uuid4()))

    assert result is False


async def test_confirm_payment_returns_false_when_wrong_status(svc: Any) -> None:
    disbursed = _make_invoice(status=InvoiceStatus.DISBURSED)
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.get = AsyncMock(return_value=disbursed)

    with patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)):
        result = await svc.confirm_payment(str(disbursed.id))

    assert result is False


async def test_confirm_payment_returns_false_when_no_wallet(svc: Any) -> None:
    invoice = _make_invoice(escrow_wallet=None)
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.get = AsyncMock(return_value=invoice)

    with patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)):
        result = await svc.confirm_payment(str(invoice.id))

    assert result is False


async def test_confirm_payment_returns_false_when_balance_insufficient(svc: Any) -> None:
    wallet = _make_wallet()
    invoice = _make_invoice(escrow_wallet=wallet)
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.get = AsyncMock(return_value=invoice)

    svc.escrow.verify_payment_received = AsyncMock(return_value=None)

    with patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)):
        result = await svc.confirm_payment(str(invoice.id))

    assert result is False


async def test_confirm_payment_returns_true_on_success(svc: Any) -> None:
    wallet = _make_wallet()
    invoice = _make_invoice(escrow_wallet=wallet)
    tx_details = {
        "transaction_id": "tx-123",
        "tx_hash": "0xHASH",
        "tx_url": "https://explorer/tx/0xHASH",
        "from_address": "0xPAYER",
    }

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.get = AsyncMock(return_value=invoice)

    svc.escrow.verify_payment_received = AsyncMock(return_value=tx_details)

    with (
        patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)),
        patch(
            "app.services.invoice_service.InvoiceRepository.mark_pending_release",
            AsyncMock(return_value=invoice),
        ),
    ):
        result = await svc.confirm_payment(str(invoice.id))

    assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# disburse_session_invoices
# ─────────────────────────────────────────────────────────────────────────────


async def test_disburse_session_invoices_calls_two_transfers(svc: Any) -> None:
    wallet = _make_wallet()
    invoice = _make_invoice(
        status=InvoiceStatus.PENDING_RELEASE,
        escrow_wallet=wallet,
        agent_payout=Decimal("95.000000"),
        marketplace_fee=Decimal("5.000000"),
    )

    agent_tx = {"id": "agent-tx-1", "txHash": "0xAGENT"}
    fee_tx = {"id": "fee-tx-1", "txHash": "0xFEE"}

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    svc.circle.create_transfer = AsyncMock(side_effect=[agent_tx, fee_tx])
    svc.circle.wait_for_transfer_completion = AsyncMock(side_effect=[agent_tx, fee_tx])
    svc.escrow.release_wallet = AsyncMock(return_value=True)

    with (
        patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)),
        patch(
            "app.services.invoice_service.InvoiceRepository.get_pending_release_by_session",
            AsyncMock(return_value=[invoice]),
        ),
        patch("app.services.invoice_service.InvoiceRepository.mark_disbursing", AsyncMock()),
        patch("app.services.invoice_service.InvoiceRepository.mark_disbursed", AsyncMock()),
    ):
        results = await svc.disburse_session_invoices(str(uuid.uuid4()))

    assert len(results) == 1
    assert results[0]["success"] is True
    assert svc.circle.create_transfer.call_count == 2


async def test_disburse_session_invoices_returns_failure_on_transfer_error(svc: Any) -> None:
    wallet = _make_wallet()
    invoice = _make_invoice(status=InvoiceStatus.PENDING_RELEASE, escrow_wallet=wallet)

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    svc.circle.create_transfer = AsyncMock(side_effect=RuntimeError("Circle API down"))

    with (
        patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)),
        patch(
            "app.services.invoice_service.InvoiceRepository.get_pending_release_by_session",
            AsyncMock(return_value=[invoice]),
        ),
        patch("app.services.invoice_service.InvoiceRepository.mark_disbursing", AsyncMock()),
        patch("app.services.invoice_service.InvoiceRepository.mark_failed", AsyncMock()),
    ):
        results = await svc.disburse_session_invoices(str(uuid.uuid4()))

    assert len(results) == 1
    assert results[0]["success"] is False
    assert "Circle API down" in results[0]["error"]


async def test_disburse_session_invoices_empty_session(svc: Any) -> None:
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    with (
        patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)),
        patch(
            "app.services.invoice_service.InvoiceRepository.get_pending_release_by_session",
            AsyncMock(return_value=[]),
        ),
    ):
        results = await svc.disburse_session_invoices(str(uuid.uuid4()))

    assert results == []


# ─────────────────────────────────────────────────────────────────────────────
# expire_unpaid_invoices
# ─────────────────────────────────────────────────────────────────────────────


async def test_expire_unpaid_invoices_returns_count(svc: Any) -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    expired = [
        _make_invoice(expires_at=past, escrow_wallet_id=None),
        _make_invoice(expires_at=past, escrow_wallet_id=None),
    ]

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()

    with (
        patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)),
        patch(
            "app.services.invoice_service.InvoiceRepository.get_expired_unpaid",
            AsyncMock(return_value=expired),
        ),
        patch("app.services.invoice_service.InvoiceRepository.mark_expired", AsyncMock()),
    ):
        count = await svc.expire_unpaid_invoices()

    assert count == 2


async def test_expire_unpaid_invoices_releases_locked_wallets(svc: Any) -> None:
    wallet_id = uuid.uuid4()
    past = datetime.now(UTC) - timedelta(hours=1)
    expired = [_make_invoice(expires_at=past, escrow_wallet_id=wallet_id)]

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()

    svc.escrow.release_wallet = AsyncMock()

    with (
        patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)),
        patch(
            "app.services.invoice_service.InvoiceRepository.get_expired_unpaid",
            AsyncMock(return_value=expired),
        ),
        patch("app.services.invoice_service.InvoiceRepository.mark_expired", AsyncMock()),
    ):
        await svc.expire_unpaid_invoices()

    svc.escrow.release_wallet.assert_called_once_with(str(wallet_id))


async def test_expire_unpaid_invoices_zero_when_none_expired(svc: Any) -> None:
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()

    with (
        patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)),
        patch(
            "app.services.invoice_service.InvoiceRepository.get_expired_unpaid",
            AsyncMock(return_value=[]),
        ),
    ):
        count = await svc.expire_unpaid_invoices()

    assert count == 0


# ─────────────────────────────────────────────────────────────────────────────
# handle_payment_webhook
# ─────────────────────────────────────────────────────────────────────────────


async def test_handle_payment_webhook_returns_false_for_missing_wallet_id(svc: Any) -> None:
    payload: dict[str, Any] = {"notification": {"transaction": {"id": "tx-1"}}}
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute.return_value = scalar_mock

    with patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)):
        result = await svc.handle_payment_webhook(payload)

    assert result is False


async def test_handle_payment_webhook_returns_false_for_amount_mismatch(svc: Any) -> None:
    invoice_id = uuid.uuid4()
    wallet = _make_wallet(locked_invoice_id=invoice_id)
    invoice = _make_invoice(
        id=invoice_id,
        status=InvoiceStatus.PENDING,
        amount=Decimal("50.000000"),
    )

    payload: dict[str, Any] = {
        "notification": {
            "transaction": {
                "walletId": "circle-wallet-001",
                "id": "tx-1",
                "amounts": [{"amount": "10.0"}],  # less than invoice amount
            }
        }
    }

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    scalar_mock = MagicMock()
    scalar_mock.scalar_one_or_none = MagicMock(return_value=wallet)
    mock_session.execute = AsyncMock(return_value=scalar_mock)

    with (
        patch("app.services.invoice_service.AsyncSessionLocal", _session_factory(mock_session)),
        patch(
            "app.services.invoice_service.InvoiceRepository.get_by_id",
            AsyncMock(return_value=invoice),
        ),
    ):
        result = await svc.handle_payment_webhook(payload)

    assert result is False
