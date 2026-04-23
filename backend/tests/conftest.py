"""
Shared test configuration and fixtures.

Each test that uses `db_session` gets a fresh SQLite in-memory database —
tables are created before the test runs and the engine is disposed after,
giving true per-test isolation at essentially zero cost.
"""
import os

# Must be set before any app module is imported so pydantic-settings can
# construct the Settings object without requiring a real .env file.
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32c")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-testing-only-32c")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/testdb")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql+psycopg2://test:test@localhost/testdb")

import uuid
from decimal import Decimal

import pytest

# ── SQLite compatibility patches ───────────────────────────────────────────────
# SQLite's type compiler doesn't know about PostgreSQL-specific types.
# Patch it once here so `create_all` works without touching the production models.

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # noqa: E402


def _sqlite_visit_JSONB(self, type_, **kw) -> str:  # type: ignore[no-untyped-def]
    return "JSON"


SQLiteTypeCompiler.visit_JSONB = _sqlite_visit_JSONB  # type: ignore[attr-defined]
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.agents import Agent, AgentHostingType, AgentStatus
from app.models.base import Base
from app.models.invoices import Invoice, InvoiceStatus
from app.models.jobs import Job, JobStatus
from app.models.sessions import ConnectionType, Session, SessionPhase
from app.models.users import User, UserRole, UserStatus
from app.repositories.agent_repo import AgentRepository
from app.repositories.invoice_repo import InvoiceRepository
from app.repositories.job_repo import JobRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.user_repo import UserRepository


# ──────────────────────────────────────────────────────────────────────────────
# Core session fixture — fresh in-memory DB per test
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


# ──────────────────────────────────────────────────────────────────────────────
# Entity factory helpers
# Call these inside tests (not as fixtures) so each test controls its own data.
# ──────────────────────────────────────────────────────────────────────────────

async def make_user(session: AsyncSession, **kwargs) -> User:
    defaults: dict = dict(
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        role=UserRole.BUYER,
        status=UserStatus.ACTIVE,
        email_verified=False,
        kyc_verified=False,
        notification_preferences={},
    )
    defaults.update(kwargs)
    return await UserRepository(session).create(**defaults)


async def make_agent(session: AsyncSession, owner_id: uuid.UUID, **kwargs) -> Agent:
    defaults: dict = dict(
        owner_id=owner_id,
        name="Test Agent",
        slug=f"test-agent-{uuid.uuid4().hex[:8]}",
        description="A test service agent",
        hosting_type=AgentHostingType.EXTERNALLY_HOSTED,
        base_url="https://agent.example.com",
        status=AgentStatus.ACTIVE,
        categories=[],
        tags=[],
        pricing_summary={},
    )
    defaults.update(kwargs)
    return await AgentRepository(session).create(**defaults)


async def make_session(session: AsyncSession, user_id: uuid.UUID, **kwargs) -> Session:
    defaults: dict = dict(
        user_id=user_id,
        phase=SessionPhase.ACTIVE,
        connection_type=ConnectionType.WEBSOCKET,
        job_session_auth_token=f"tok-{uuid.uuid4().hex}",
        graph_state={},
    )
    defaults.update(kwargs)
    return await SessionRepository(session).create(**defaults)


async def make_job(
    session: AsyncSession,
    session_id: uuid.UUID,
    buyer_id: uuid.UUID,
    agent_id: uuid.UUID,
    **kwargs,
) -> Job:
    defaults: dict = dict(
        session_id=session_id,
        buyer_id=buyer_id,
        agent_id=agent_id,
        status=JobStatus.AWAITING_INVOICE,
    )
    defaults.update(kwargs)
    return await JobRepository(session).create(**defaults)


async def make_invoice(
    session: AsyncSession,
    job_id: uuid.UUID,
    session_id: uuid.UUID,
    buyer_id: uuid.UUID,
    agent_id: uuid.UUID,
    **kwargs,
) -> Invoice:
    defaults: dict = dict(
        job_id=job_id,
        session_id=session_id,
        buyer_id=buyer_id,
        agent_id=agent_id,
        amount=Decimal("10.000000"),
        currency="USDC",
        status=InvoiceStatus.PENDING,
        payment_function_name="pay_invoice",
    )
    defaults.update(kwargs)
    return await InvoiceRepository(session).create(**defaults)
