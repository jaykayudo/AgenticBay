import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sessions import SessionPhase
from app.repositories.session_repo import SessionRepository
from tests.conftest import make_session, make_user

# ── create ────────────────────────────────────────────────────────────────────


async def test_create_session(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    sess = await make_session(db_session, user.id)
    assert sess.id is not None
    assert sess.user_id == user.id
    assert sess.phase == SessionPhase.ACTIVE


# ── get_active_sessions ───────────────────────────────────────────────────────


async def test_get_active_sessions_excludes_closed(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    active = await make_session(db_session, user.id, phase=SessionPhase.ACTIVE)
    searching = await make_session(db_session, user.id, phase=SessionPhase.SEARCHING)
    await make_session(db_session, user.id, phase=SessionPhase.CLOSED)

    repo = SessionRepository(db_session)
    results = await repo.get_active_sessions()
    ids = {r.id for r in results}
    assert active.id in ids
    assert searching.id in ids
    # Closed session must not appear
    closed_sessions = [r for r in results if r.phase == SessionPhase.CLOSED]
    assert closed_sessions == []


async def test_get_active_sessions_all_closed_returns_empty(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    await make_session(db_session, user.id, phase=SessionPhase.CLOSED)
    results = await SessionRepository(db_session).get_active_sessions()
    assert results == []


async def test_get_active_sessions_respects_limit(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    for _ in range(5):
        await make_session(db_session, user.id, phase=SessionPhase.ACTIVE)
    results = await SessionRepository(db_session).get_active_sessions(limit=2)
    assert len(results) == 2


# ── mark_closed ───────────────────────────────────────────────────────────────


async def test_mark_closed_sets_phase_and_timestamp(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    sess = await make_session(db_session, user.id, phase=SessionPhase.ACTIVE)
    repo = SessionRepository(db_session)
    closed = await repo.mark_closed(sess.id)
    assert closed is not None
    assert closed.phase == SessionPhase.CLOSED
    assert closed.closed_at is not None


async def test_mark_closed_unknown_returns_none(db_session: AsyncSession) -> None:
    result = await SessionRepository(db_session).mark_closed(uuid.uuid4())
    assert result is None


# ── get_by_user ───────────────────────────────────────────────────────────────


async def test_get_by_user_returns_only_that_users_sessions(db_session: AsyncSession) -> None:
    user1 = await make_user(db_session)
    user2 = await make_user(db_session)
    s1 = await make_session(db_session, user1.id)
    s2 = await make_session(db_session, user1.id)
    await make_session(db_session, user2.id)

    results = await SessionRepository(db_session).get_by_user(user1.id)
    ids = {r.id for r in results}
    assert s1.id in ids
    assert s2.id in ids
    assert len(results) == 2


async def test_get_by_user_no_sessions(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    results = await SessionRepository(db_session).get_by_user(user.id)
    assert results == []
