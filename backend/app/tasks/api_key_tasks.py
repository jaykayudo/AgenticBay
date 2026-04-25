from __future__ import annotations

import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.repositories.api_key_repo import ApiKeyRepository

logger = logging.getLogger(__name__)


async def expire_old_keys_task() -> None:
    """Run daily — mark expired API keys inactive."""
    while True:
        try:
            async with AsyncSessionLocal() as session:
                count = await ApiKeyRepository(session).expire_stale_keys()
                await session.commit()
            if count:
                logger.info("Expired %d API key(s)", count)
        except Exception:
            logger.exception("expire_old_keys_task error")
        await asyncio.sleep(24 * 60 * 60)


async def cleanup_old_audit_logs_task() -> None:
    """Run weekly — delete API-key audit logs older than one year."""
    while True:
        try:
            async with AsyncSessionLocal() as session:
                count = await ApiKeyRepository(session).delete_old_audit_logs()
                await session.commit()
            if count:
                logger.info("Deleted %d old API key audit log(s)", count)
        except Exception:
            logger.exception("cleanup_old_audit_logs_task error")
        await asyncio.sleep(7 * 24 * 60 * 60)


async def detect_suspicious_activity_task() -> None:
    """Placeholder task for future anomaly detection alerts."""
    while True:
        await asyncio.sleep(5 * 60)
