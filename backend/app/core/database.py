from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

_asyncpg_pool: asyncpg.Pool | None = None


async def get_asyncpg_pool() -> asyncpg.Pool:
    global _asyncpg_pool
    if _asyncpg_pool is None:
        dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        _asyncpg_pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    return _asyncpg_pool


async def close_asyncpg_pool() -> None:
    global _asyncpg_pool
    if _asyncpg_pool is not None:
        await _asyncpg_pool.close()
        _asyncpg_pool = None


@asynccontextmanager
async def asyncpg_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    pool = await get_asyncpg_pool()
    async with pool.acquire() as conn:
        yield conn


_engine_kwargs: dict[str, Any] = {
    "echo": settings.DEBUG,
    "pool_pre_ping": True,
}
if settings.APP_ENV == "testing":
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables from metadata. For test environments only."""
    from app.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
