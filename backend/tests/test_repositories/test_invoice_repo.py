import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoices import InvoiceStatus
from app.repositories.invoice_repo import InvoiceRepository
from tests.conftest import make_agent, make_invoice, make_job, make_session, make_user


async def _setup(db_session: AsyncSession):
    """Return (user, agent, sess, job) wired together."""
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    sess = await make_session(db_session, user.id)
    job = await make_job(db_session, sess.id, user.id, agent.id)
    return user, agent, sess, job


# ── create ────────────────────────────────────────────────────────────────────


async def test_create_invoice_defaults_to_pending(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)
    assert invoice.id is not None
    assert invoice.status == InvoiceStatus.PENDING
    assert invoice.paid_at is None
    assert invoice.disbursed_at is None


async def test_create_invoice_stores_fee_split(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(
        db_session,
        job.id,
        sess.id,
        user.id,
        agent.id,
        amount=Decimal("100.000000"),
        marketplace_fee=Decimal("5.000000"),
        agent_payout=Decimal("95.000000"),
    )
    assert invoice.marketplace_fee == Decimal("5.000000")
    assert invoice.agent_payout == Decimal("95.000000")


# ── get_by_session ────────────────────────────────────────────────────────────


async def test_get_by_session_returns_invoices_for_that_session(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    sess1 = await make_session(db_session, user.id)
    sess2 = await make_session(db_session, user.id)
    job1 = await make_job(db_session, sess1.id, user.id, agent.id)
    job2 = await make_job(db_session, sess2.id, user.id, agent.id)

    inv1 = await make_invoice(db_session, job1.id, sess1.id, user.id, agent.id)
    await make_invoice(db_session, job2.id, sess2.id, user.id, agent.id)

    results = await InvoiceRepository(db_session).get_by_session(sess1.id)
    assert len(results) == 1
    assert results[0].id == inv1.id


async def test_get_by_session_empty(db_session: AsyncSession) -> None:
    results = await InvoiceRepository(db_session).get_by_session(uuid.uuid4())
    assert results == []


# ── get_expired_unpaid ────────────────────────────────────────────────────────


async def test_get_expired_unpaid_returns_past_expiry_invoices(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    past = datetime.now(UTC) - timedelta(hours=1)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id, expires_at=past)

    results = await InvoiceRepository(db_session).get_expired_unpaid(datetime.now(UTC))
    assert any(r.id == invoice.id for r in results)


async def test_get_expired_unpaid_ignores_future_expiry(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    future = datetime.now(UTC) + timedelta(hours=1)
    await make_invoice(db_session, job.id, sess.id, user.id, agent.id, expires_at=future)

    results = await InvoiceRepository(db_session).get_expired_unpaid(datetime.now(UTC))
    assert results == []


# ── mark_payment_checking ─────────────────────────────────────────────────────


async def test_mark_payment_checking_transitions_status(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)

    updated = await InvoiceRepository(db_session).mark_payment_checking(invoice.id)
    assert updated is not None
    assert updated.status == InvoiceStatus.PAYMENT_CHECKING


# ── mark_pending_release ──────────────────────────────────────────────────────


async def test_mark_pending_release_sets_status_paid_at_and_tx(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)

    updated = await InvoiceRepository(db_session).mark_pending_release(
        invoice.id,
        payment_transaction_id="tx-001",
        payment_tx_hash="0xABC",
        payment_tx_url="https://explorer.example.com/tx/0xABC",
        payer_wallet_address="0xPAYER",
    )
    assert updated is not None
    assert updated.status == InvoiceStatus.PENDING_RELEASE
    assert updated.paid_at is not None
    assert updated.payment_transaction_id == "tx-001"
    assert updated.payment_tx_hash == "0xABC"
    assert updated.payer_wallet_address == "0xPAYER"


async def test_mark_pending_release_unknown_returns_none(db_session: AsyncSession) -> None:
    result = await InvoiceRepository(db_session).mark_pending_release(
        uuid.uuid4(), payment_transaction_id="tx-x"
    )
    assert result is None


# ── mark_disbursing ───────────────────────────────────────────────────────────


async def test_mark_disbursing_transitions_status(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)

    updated = await InvoiceRepository(db_session).mark_disbursing(invoice.id)
    assert updated is not None
    assert updated.status == InvoiceStatus.DISBURSING


# ── mark_disbursed ────────────────────────────────────────────────────────────


async def test_mark_disbursed_sets_status_and_timestamp(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)

    updated = await InvoiceRepository(db_session).mark_disbursed(invoice.id)
    assert updated is not None
    assert updated.status == InvoiceStatus.DISBURSED
    assert updated.disbursed_at is not None


async def test_mark_disbursed_records_tx_ids(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)

    updated = await InvoiceRepository(db_session).mark_disbursed(
        invoice.id,
        agent_disbursement_tx_id="agent-tx-1",
        agent_disbursement_tx_hash="0xAGENT",
        fee_disbursement_tx_id="fee-tx-1",
        fee_disbursement_tx_hash="0xFEE",
    )
    assert updated is not None
    assert updated.agent_disbursement_tx_id == "agent-tx-1"
    assert updated.agent_disbursement_tx_hash == "0xAGENT"
    assert updated.fee_disbursement_tx_id == "fee-tx-1"
    assert updated.fee_disbursement_tx_hash == "0xFEE"


async def test_mark_disbursed_unknown_returns_none(db_session: AsyncSession) -> None:
    result = await InvoiceRepository(db_session).mark_disbursed(uuid.uuid4())
    assert result is None


# ── mark_refunded ─────────────────────────────────────────────────────────────


async def test_mark_refunded_sets_status_and_timestamp(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)

    updated = await InvoiceRepository(db_session).mark_refunded(
        invoice.id, refund_tx_id="ref-001", refund_tx_hash="0xREFUND"
    )
    assert updated is not None
    assert updated.status == InvoiceStatus.REFUNDED
    assert updated.refunded_at is not None
    assert updated.refund_tx_id == "ref-001"
    assert updated.refund_tx_hash == "0xREFUND"


# ── mark_failed ───────────────────────────────────────────────────────────────


async def test_mark_failed_transitions_status(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)

    updated = await InvoiceRepository(db_session).mark_failed(invoice.id)
    assert updated is not None
    assert updated.status == InvoiceStatus.FAILED


# ── mark_expired ──────────────────────────────────────────────────────────────


async def test_mark_expired_transitions_status(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)

    updated = await InvoiceRepository(db_session).mark_expired(invoice.id)
    assert updated is not None
    assert updated.status == InvoiceStatus.EXPIRED
