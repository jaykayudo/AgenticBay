from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from app.core.database import AsyncSessionLocal
from app.repositories.agent_repo import AgentRepository
from app.services.health_client import (
    MAX_CONSECUTIVE_FAILURES_BEFORE_SUSPEND,
    AgentHealthClient,
)

logger = logging.getLogger(__name__)

_HEALTH_CHECK_INTERVAL = 60  # seconds between full sweeps
_CONCURRENCY_LIMIT = 20  # max simultaneous health checks


async def health_check_all_agents_task() -> None:
    """Runs every 60 seconds — checks all ACTIVE agents and auto-suspends chronic failures."""
    while True:
        try:
            await _run_health_sweep()
        except Exception:
            logger.exception("health_check_all_agents_task: unhandled error in sweep")
        await asyncio.sleep(_HEALTH_CHECK_INTERVAL)


async def _run_health_sweep() -> None:
    async with AsyncSessionLocal() as db:
        repo = AgentRepository(db)
        agents = await repo.get_all_active_for_health_check()

    if not agents:
        return

    logger.info("Health sweep: checking %d active agent(s)", len(agents))
    semaphore = asyncio.Semaphore(_CONCURRENCY_LIMIT)

    async def check_one(agent_id: uuid.UUID, base_url: str, owner_id: uuid.UUID) -> None:
        async with semaphore:
            await _check_and_persist(agent_id, base_url, owner_id)

    await asyncio.gather(*[check_one(a, b, o) for a, b, o in agents])


async def _check_and_persist(
    agent_id: uuid.UUID,
    base_url: str,
    owner_id: uuid.UUID,
) -> None:

    client = AgentHealthClient()
    result = await client.check(base_url)
    now = datetime.now(UTC)

    async with AsyncSessionLocal() as db:
        repo = AgentRepository(db)
        agent = await repo.get_by_id(agent_id)
        if agent is None:
            return

        prev_failures = agent.consecutive_health_failures or 0
        is_pass = result.healthy and result.ready

        if is_pass:
            new_failures = 0
        else:
            new_failures = prev_failures + 1

        await repo.update_health_status(
            agent_id,
            status=result.status,
            checked_at=now,
            consecutive_failures=new_failures,
            agent_version=result.agent_version,
        )
        await db.commit()

    # Update Redis cache
    await client.set_cached(str(agent_id), result, new_failures)

    if is_pass:
        logger.debug("Health OK: agent=%s (%.0fms)", agent_id, result.response_time_ms)
        return

    logger.warning(
        "Health FAIL: agent=%s failures=%d reason=%s",
        agent_id,
        new_failures,
        result.reason,
    )

    # First failure — warn owner immediately
    if new_failures == 1:
        await _notify_owner(
            owner_id=owner_id,
            agent_id=agent_id,
            notification_type="AGENT_HEALTH_DEGRADED",
            title="Your agent failed a health check",
            body=(
                f"Your agent at {base_url} failed its first health check. "
                f"Reason: {result.reason or result.status}. "
                "If this continues, the agent will be automatically suspended after "
                f"{MAX_CONSECUTIVE_FAILURES_BEFORE_SUSPEND} consecutive failures."
            ),
        )

    # Threshold reached — auto-suspend
    if new_failures >= MAX_CONSECUTIVE_FAILURES_BEFORE_SUSPEND:
        await _suspend_agent(agent_id, base_url, owner_id, new_failures, result.reason)


async def _suspend_agent(
    agent_id: uuid.UUID,
    base_url: str,
    owner_id: uuid.UUID,
    failure_count: int,
    reason: str | None,
) -> None:
    from app.models.agents import AgentStatus

    async with AsyncSessionLocal() as db:
        repo = AgentRepository(db)
        agent = await repo.get_by_id(agent_id)
        if agent is None or agent.status != AgentStatus.ACTIVE:
            return
        await repo.update(agent_id, status=AgentStatus.SUSPENDED)
        await db.commit()

    logger.warning(
        "Auto-suspended agent=%s after %d consecutive health failures", agent_id, failure_count
    )

    await _notify_owner(
        owner_id=owner_id,
        agent_id=agent_id,
        notification_type="AGENT_SUSPENDED",
        title="Your agent has been automatically suspended",
        body=(
            f"Your agent at {base_url} has been suspended after "
            f"{failure_count} consecutive failed health checks. "
            f"Last reported reason: {reason or 'unreachable'}. "
            "Please fix the issue and contact support to reactivate."
        ),
    )


async def _notify_owner(
    *,
    owner_id: uuid.UUID,
    agent_id: uuid.UUID,
    notification_type: str,
    title: str,
    body: str,
) -> None:
    try:
        from app.models.notifications import NotificationType
        from app.services.notification_service import NotificationService

        async with AsyncSessionLocal() as db:
            svc = NotificationService(db)
            await svc.create_notification(
                user_id=owner_id,
                notification_type=NotificationType(notification_type),
                title=title,
                body=body,
                data={"agent_id": str(agent_id)},
                enqueue_email=False,
            )
    except Exception:
        logger.exception("Failed to notify owner=%s for agent=%s", owner_id, agent_id)
