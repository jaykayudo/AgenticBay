import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jobs import JobStatus
from app.repositories.job_repo import JobRepository
from tests.conftest import make_agent, make_job, make_session, make_user


# ── create_job ────────────────────────────────────────────────────────────────

async def test_create_job_sets_awaiting_invoice_status(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    sess = await make_session(db_session, user.id)
    job = await JobRepository(db_session).create_job(
        session_id=sess.id,
        buyer_id=user.id,
        agent_id=agent.id,
    )
    assert job.id is not None
    assert job.status == JobStatus.AWAITING_INVOICE
    assert job.started_at is not None


async def test_create_job_with_raw_request(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    sess = await make_session(db_session, user.id)
    job = await JobRepository(db_session).create_job(
        session_id=sess.id,
        buyer_id=user.id,
        agent_id=agent.id,
        raw_user_request="I need a weather report",
    )
    assert job.raw_user_request == "I need a weather report"


# ── mark_completed ────────────────────────────────────────────────────────────

async def test_mark_completed_sets_status_and_timestamp(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    sess = await make_session(db_session, user.id)
    job = await make_job(db_session, sess.id, user.id, agent.id)

    updated = await JobRepository(db_session).mark_completed(job.id)
    assert updated is not None
    assert updated.status == JobStatus.COMPLETED
    assert updated.completed_at is not None


async def test_mark_completed_unknown_returns_none(db_session: AsyncSession) -> None:
    result = await JobRepository(db_session).mark_completed(uuid.uuid4())
    assert result is None


# ── get_by_session ────────────────────────────────────────────────────────────

async def test_get_by_session_returns_correct_jobs(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    sess1 = await make_session(db_session, user.id)
    sess2 = await make_session(db_session, user.id)

    j1 = await make_job(db_session, sess1.id, user.id, agent.id)
    j2 = await make_job(db_session, sess1.id, user.id, agent.id)
    await make_job(db_session, sess2.id, user.id, agent.id)

    results = await JobRepository(db_session).get_by_session(sess1.id)
    ids = {r.id for r in results}
    assert j1.id in ids
    assert j2.id in ids
    assert len(results) == 2


async def test_get_by_session_empty(db_session: AsyncSession) -> None:
    results = await JobRepository(db_session).get_by_session(uuid.uuid4())
    assert results == []


# ── get_by_buyer ──────────────────────────────────────────────────────────────

async def test_get_by_buyer_returns_correct_jobs(db_session: AsyncSession) -> None:
    buyer1 = await make_user(db_session)
    buyer2 = await make_user(db_session)
    agent = await make_agent(db_session, buyer1.id)
    sess1 = await make_session(db_session, buyer1.id)
    sess2 = await make_session(db_session, buyer2.id)

    j1 = await make_job(db_session, sess1.id, buyer1.id, agent.id)
    j2 = await make_job(db_session, sess1.id, buyer1.id, agent.id)
    await make_job(db_session, sess2.id, buyer2.id, agent.id)

    results = await JobRepository(db_session).get_by_buyer(buyer1.id)
    ids = {r.id for r in results}
    assert j1.id in ids
    assert j2.id in ids
    assert len(results) == 2


async def test_get_by_buyer_empty(db_session: AsyncSession) -> None:
    results = await JobRepository(db_session).get_by_buyer(uuid.uuid4())
    assert results == []
