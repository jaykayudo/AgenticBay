"""
Tests for DB-level constraints (UNIQUE, CHECK).

Each constraint test wraps the violating statement in a savepoint so the
session stays usable afterwards — and each test still gets its own fresh DB.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AgentAnalytic, AnalyticPeriod
from app.models.auth import AuthProviderType, UserAuthProvider
from app.models.reviews import Review, ReviewStatus
from app.repositories.agent_repo import AgentRepository
from tests.conftest import (
    make_agent,
    make_invoice,
    make_job,
    make_session,
    make_user,
)

# ──────────────────────────────────────────────────────────────────────────────
# Review — unique job_id
# ──────────────────────────────────────────────────────────────────────────────


async def test_review_unique_per_job(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    sess = await make_session(db_session, user.id)
    job = await make_job(db_session, sess.id, user.id, agent.id)

    # First review succeeds
    db_session.add(
        Review(
            job_id=job.id,
            reviewer_id=user.id,
            agent_id=agent.id,
            rating=4,
            status=ReviewStatus.PUBLISHED,
            verified_purchase=False,
            helpful_votes=0,
        )
    )
    await db_session.flush()

    # Second review on the same job must fail
    async with db_session.begin_nested():
        with pytest.raises(IntegrityError):
            db_session.add(
                Review(
                    job_id=job.id,
                    reviewer_id=user.id,
                    agent_id=agent.id,
                    rating=3,
                    status=ReviewStatus.PENDING,
                    verified_purchase=False,
                    helpful_votes=0,
                )
            )
            await db_session.flush()


# ──────────────────────────────────────────────────────────────────────────────
# Review — rating CHECK constraint  (1–5)
# ──────────────────────────────────────────────────────────────────────────────


async def test_review_rating_below_minimum_rejected(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    sess = await make_session(db_session, user.id)
    job = await make_job(db_session, sess.id, user.id, agent.id)

    async with db_session.begin_nested():
        with pytest.raises(IntegrityError):
            db_session.add(
                Review(
                    job_id=job.id,
                    reviewer_id=user.id,
                    agent_id=agent.id,
                    rating=0,
                    status=ReviewStatus.PENDING,
                    verified_purchase=False,
                    helpful_votes=0,
                )
            )
            await db_session.flush()


async def test_review_rating_above_maximum_rejected(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    sess = await make_session(db_session, user.id)
    job = await make_job(db_session, sess.id, user.id, agent.id)

    async with db_session.begin_nested():
        with pytest.raises(IntegrityError):
            db_session.add(
                Review(
                    job_id=job.id,
                    reviewer_id=user.id,
                    agent_id=agent.id,
                    rating=6,
                    status=ReviewStatus.PENDING,
                    verified_purchase=False,
                    helpful_votes=0,
                )
            )
            await db_session.flush()


async def test_review_valid_ratings_accepted(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)

    # Each rating (1–5) needs a distinct job
    for rating in range(1, 6):
        sess = await make_session(db_session, user.id)
        job = await make_job(db_session, sess.id, user.id, agent.id)
        db_session.add(
            Review(
                job_id=job.id,
                reviewer_id=user.id,
                agent_id=agent.id,
                rating=rating,
                status=ReviewStatus.PUBLISHED,
                verified_purchase=False,
                helpful_votes=0,
            )
        )
    await db_session.flush()  # all five must succeed


# ──────────────────────────────────────────────────────────────────────────────
# AgentAnalytic — unique (agent_id, period, period_start)
# ──────────────────────────────────────────────────────────────────────────────


async def test_agent_analytic_duplicate_period_rejected(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    today = date.today()

    db_session.add(
        AgentAnalytic(
            agent_id=agent.id,
            period=AnalyticPeriod.DAILY,
            period_start=today,
            total_jobs=5,
            successful_jobs=4,
            failed_jobs=1,
            total_revenue=Decimal("50"),
            action_breakdown={},
        )
    )
    await db_session.flush()

    async with db_session.begin_nested():
        with pytest.raises(IntegrityError):
            db_session.add(
                AgentAnalytic(
                    agent_id=agent.id,
                    period=AnalyticPeriod.DAILY,
                    period_start=today,  # same (agent, period, date) → duplicate
                    total_jobs=10,
                    successful_jobs=9,
                    failed_jobs=1,
                    total_revenue=Decimal("100"),
                    action_breakdown={},
                )
            )
            await db_session.flush()


async def test_agent_analytic_different_period_accepted(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    today = date.today()

    for period in AnalyticPeriod:
        db_session.add(
            AgentAnalytic(
                agent_id=agent.id,
                period=period,
                period_start=today,
                total_jobs=1,
                successful_jobs=1,
                failed_jobs=0,
                total_revenue=Decimal("10"),
                action_breakdown={},
            )
        )
    await db_session.flush()  # DAILY, WEEKLY, MONTHLY all different → all OK


# ──────────────────────────────────────────────────────────────────────────────
# UserAuthProvider — unique (user_id, provider)
# ──────────────────────────────────────────────────────────────────────────────


async def test_auth_provider_duplicate_user_provider_rejected(db_session: AsyncSession) -> None:
    user = await make_user(db_session)

    db_session.add(
        UserAuthProvider(
            user_id=user.id,
            provider=AuthProviderType.GOOGLE,
            provider_user_id="google-sub-001",
            provider_data={},
        )
    )
    await db_session.flush()

    async with db_session.begin_nested():
        with pytest.raises(IntegrityError):
            db_session.add(
                UserAuthProvider(
                    user_id=user.id,
                    provider=AuthProviderType.GOOGLE,  # same user + same provider
                    provider_user_id="google-sub-002",
                    provider_data={},
                )
            )
            await db_session.flush()


async def test_auth_provider_different_provider_accepted(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    for provider in AuthProviderType:
        db_session.add(
            UserAuthProvider(
                user_id=user.id,
                provider=provider,
                provider_user_id=f"uid-{provider}",
                provider_data={},
            )
        )
    await db_session.flush()


# ──────────────────────────────────────────────────────────────────────────────
# UserAuthProvider — unique (provider, provider_user_id)
# ──────────────────────────────────────────────────────────────────────────────


async def test_auth_provider_duplicate_provider_uid_rejected(db_session: AsyncSession) -> None:
    user1 = await make_user(db_session)
    user2 = await make_user(db_session)

    db_session.add(
        UserAuthProvider(
            user_id=user1.id,
            provider=AuthProviderType.GOOGLE,
            provider_user_id="shared-google-sub",
            provider_data={},
        )
    )
    await db_session.flush()

    async with db_session.begin_nested():
        with pytest.raises(IntegrityError):
            db_session.add(
                UserAuthProvider(
                    user_id=user2.id,
                    provider=AuthProviderType.GOOGLE,
                    provider_user_id="shared-google-sub",  # same provider + uid
                    provider_data={},
                )
            )
            await db_session.flush()


# ──────────────────────────────────────────────────────────────────────────────
# Invoice — unique job_id (one invoice per job)
# ──────────────────────────────────────────────────────────────────────────────


async def test_invoice_unique_per_job(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent = await make_agent(db_session, user.id)
    sess = await make_session(db_session, user.id)
    job = await make_job(db_session, sess.id, user.id, agent.id)

    # First invoice succeeds
    await make_invoice(db_session, job.id, sess.id, user.id, agent.id)

    # Second invoice for the same job must fail
    async with db_session.begin_nested():
        with pytest.raises(IntegrityError):
            await make_invoice(db_session, job.id, sess.id, user.id, agent.id)


# ──────────────────────────────────────────────────────────────────────────────
# Agent — unique orchestrator_api_key
# ──────────────────────────────────────────────────────────────────────────────


async def test_agent_orchestrator_key_is_unique(db_session: AsyncSession) -> None:
    user = await make_user(db_session)
    agent1 = await make_agent(db_session, user.id)
    agent2 = await make_agent(db_session, user.id)
    assert agent1.orchestrator_api_key != agent2.orchestrator_api_key

    async with db_session.begin_nested():
        with pytest.raises(IntegrityError):
            await AgentRepository(db_session).create(
                owner_id=user.id,
                name="Collision Agent",
                slug="collision-agent",
                description="Forces a key collision",
                base_url="https://x.example.com",
                categories=[],
                tags=[],
                pricing_summary={},
                orchestrator_api_key=agent1.orchestrator_api_key,  # force duplicate
            )
