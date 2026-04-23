import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.spending_repo import AgentSpendingRepository
from tests.conftest import make_agent, make_invoice, make_job, make_session, make_user


async def _setup(db_session: AsyncSession):
    """Return (user, agent, sess, job, invoice) for spending tests."""
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    sess = await make_session(db_session, user.id)
    job = await make_job(db_session, sess.id, user.id, agent.id)
    invoice = await make_invoice(db_session, job.id, sess.id, user.id, agent.id)
    return user, agent, sess, job, invoice


# ── log_spend ─────────────────────────────────────────────────────────────────

async def test_log_spend_creates_record(db_session: AsyncSession) -> None:
    user, master_agent, sess, job, invoice = await _setup(db_session)
    sub_agent = await make_agent(db_session, user.id)

    repo = AgentSpendingRepository(db_session)
    spend = await repo.log_spend(
        job_id=job.id,
        master_agent_id=master_agent.id,
        sub_agent_id=sub_agent.id,
        invoice_id=invoice.id,
        amount=Decimal("5.000000"),
        description="Sub-agent fee",
    )
    assert spend.id is not None
    assert spend.job_id == job.id
    assert float(spend.amount) == pytest.approx(5.0)
    assert spend.description == "Sub-agent fee"


async def test_log_spend_without_description(db_session: AsyncSession) -> None:
    user, master_agent, sess, job, invoice = await _setup(db_session)
    sub_agent = await make_agent(db_session, user.id)

    spend = await AgentSpendingRepository(db_session).log_spend(
        job_id=job.id,
        master_agent_id=master_agent.id,
        sub_agent_id=sub_agent.id,
        invoice_id=invoice.id,
        amount=Decimal("1.000000"),
    )
    assert spend.description is None


# ── get_total_spent_in_job ────────────────────────────────────────────────────

async def test_get_total_spent_no_records_returns_zero(db_session: AsyncSession) -> None:
    total = await AgentSpendingRepository(db_session).get_total_spent_in_job(uuid.uuid4())
    assert total == Decimal("0")


async def test_get_total_spent_single_record(db_session: AsyncSession) -> None:
    user, master_agent, sess, job, invoice = await _setup(db_session)
    sub_agent = await make_agent(db_session, user.id)

    await AgentSpendingRepository(db_session).log_spend(
        job_id=job.id,
        master_agent_id=master_agent.id,
        sub_agent_id=sub_agent.id,
        invoice_id=invoice.id,
        amount=Decimal("7.500000"),
    )

    total = await AgentSpendingRepository(db_session).get_total_spent_in_job(job.id)
    assert float(total) == pytest.approx(7.5)


async def test_get_total_spent_multiple_records_summed(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    master_agent = await make_agent(db_session, user.id)
    sess = await make_session(db_session, user.id)
    job = await make_job(db_session, sess.id, user.id, master_agent.id)

    sub1 = await make_agent(db_session, user.id)
    sub2 = await make_agent(db_session, user.id)

    # Each sub-agent needs its own invoice (unique job_id constraint per invoice)
    # We reuse one invoice for simplicity — spending records don't require unique invoices
    inv = await make_invoice(db_session, job.id, sess.id, user.id, master_agent.id)

    repo = AgentSpendingRepository(db_session)
    await repo.log_spend(job.id, master_agent.id, sub1.id, inv.id, Decimal("3.000000"))
    await repo.log_spend(job.id, master_agent.id, sub2.id, inv.id, Decimal("4.500000"))

    total = await repo.get_total_spent_in_job(job.id)
    assert float(total) == pytest.approx(7.5)


async def test_get_total_spent_filtered_by_master_agent(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    master1 = await make_agent(db_session, user.id)
    master2 = await make_agent(db_session, user.id)
    sub = await make_agent(db_session, user.id)

    sess = await make_session(db_session, user.id)
    job = await make_job(db_session, sess.id, user.id, master1.id)
    inv = await make_invoice(db_session, job.id, sess.id, user.id, master1.id)

    repo = AgentSpendingRepository(db_session)
    await repo.log_spend(job.id, master1.id, sub.id, inv.id, Decimal("10.000000"))
    await repo.log_spend(job.id, master2.id, sub.id, inv.id, Decimal("20.000000"))

    total_master1 = await repo.get_total_spent_in_job(job.id, master_agent_id=master1.id)
    total_master2 = await repo.get_total_spent_in_job(job.id, master_agent_id=master2.id)
    assert float(total_master1) == pytest.approx(10.0)
    assert float(total_master2) == pytest.approx(20.0)


import pytest
