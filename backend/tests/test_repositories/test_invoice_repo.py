import uuid

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


# ── get_by_onchain_id ─────────────────────────────────────────────────────────


async def test_get_by_onchain_id_found(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    await make_invoice(
        db_session,
        job.id,
        sess.id,
        user.id,
        agent.id,
        onchain_invoice_id="0xABC123",
    )
    result = await InvoiceRepository(db_session).get_by_onchain_id("0xABC123")
    assert result is not None
    assert result.onchain_invoice_id == "0xABC123"


async def test_get_by_onchain_id_not_found(db_session: AsyncSession) -> None:
    result = await InvoiceRepository(db_session).get_by_onchain_id("0xMISSING")
    assert result is None


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


# ── mark_paid ─────────────────────────────────────────────────────────────────


async def test_mark_paid_sets_status_and_timestamp(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)

    updated = await InvoiceRepository(db_session).mark_paid(invoice.id)
    assert updated is not None
    assert updated.status == InvoiceStatus.PAID
    assert updated.paid_at is not None


async def test_mark_paid_records_tx_hash(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)

    updated = await InvoiceRepository(db_session).mark_paid(invoice.id, payment_tx_hash="0xTXHASH")
    assert updated is not None
    assert updated.payment_tx_hash == "0xTXHASH"


async def test_mark_paid_unknown_returns_none(db_session: AsyncSession) -> None:
    result = await InvoiceRepository(db_session).mark_paid(uuid.uuid4())
    assert result is None


# ── mark_disbursed ────────────────────────────────────────────────────────────


async def test_mark_disbursed_sets_status_and_timestamp(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)
    await InvoiceRepository(db_session).mark_paid(invoice.id)

    updated = await InvoiceRepository(db_session).mark_disbursed(invoice.id)
    assert updated is not None
    assert updated.status == InvoiceStatus.DISBURSED
    assert updated.disbursed_at is not None


async def test_mark_disbursed_records_tx_hash(db_session: AsyncSession) -> None:
    user, agent, sess, job = await _setup(db_session)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)

    updated = await InvoiceRepository(db_session).mark_disbursed(
        invoice.id, disbursement_tx_hash="0xDISBURSE"
    )
    assert updated is not None
    assert updated.disbursement_tx_hash == "0xDISBURSE"


async def test_mark_disbursed_unknown_returns_none(db_session: AsyncSession) -> None:
    result = await InvoiceRepository(db_session).mark_disbursed(uuid.uuid4())
    assert result is None
