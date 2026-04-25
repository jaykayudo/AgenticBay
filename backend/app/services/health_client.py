from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.redis import get_redis

HEALTH_CHECK_TIMEOUT = 3.0  # seconds — per spec
HEALTH_CACHE_TTL = 120  # seconds
HEALTH_CACHE_PREFIX = "agent_health"
MAX_CONSECUTIVE_FAILURES_BEFORE_SUSPEND = 5


@dataclass
class HealthCheckResult:
    healthy: bool  # True if 200 + valid JSON + known status value
    ready: bool  # True if body["ready"] is True
    status: str  # "ok", "degraded", or "unreachable"
    reason: str | None  # populated when degraded or unreachable
    agent_version: str | None
    active_sessions: int | None
    response_time_ms: float


class AgentHealthClient:
    """Lightweight, unauthenticated health check for service agents."""

    # ── Live check ────────────────────────────────────────────────────────────

    async def check(self, base_url: str) -> HealthCheckResult:
        url = f"{base_url.rstrip('/')}/health"
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
                response = await client.get(url)
            elapsed = (time.monotonic() - start) * 1000
        except httpx.TimeoutException:
            return HealthCheckResult(
                healthy=False,
                ready=False,
                status="unreachable",
                reason="Health check timed out after 3 seconds",
                agent_version=None,
                active_sessions=None,
                response_time_ms=HEALTH_CHECK_TIMEOUT * 1000,
            )
        except httpx.HTTPError as exc:
            return HealthCheckResult(
                healthy=False,
                ready=False,
                status="unreachable",
                reason=f"Connection failed: {exc}",
                agent_version=None,
                active_sessions=None,
                response_time_ms=(time.monotonic() - start) * 1000,
            )

        if response.status_code != 200:
            return HealthCheckResult(
                healthy=False,
                ready=False,
                status="unreachable",
                reason=f"HTTP {response.status_code}",
                agent_version=None,
                active_sessions=None,
                response_time_ms=elapsed,
            )

        try:
            body: dict[str, Any] = response.json()
        except (ValueError, json.JSONDecodeError):
            return HealthCheckResult(
                healthy=False,
                ready=False,
                status="unreachable",
                reason="Response is not valid JSON",
                agent_version=None,
                active_sessions=None,
                response_time_ms=elapsed,
            )

        raw_status = body.get("status", "")
        if raw_status not in ("ok", "degraded"):
            return HealthCheckResult(
                healthy=False,
                ready=False,
                status="unreachable",
                reason=f"Unknown status value: {raw_status!r}",
                agent_version=None,
                active_sessions=None,
                response_time_ms=elapsed,
            )

        ready = bool(body.get("ready", False))
        return HealthCheckResult(
            healthy=True,
            ready=ready,
            status=raw_status,
            reason=body.get("reason") if raw_status == "degraded" else None,
            agent_version=body.get("version"),
            active_sessions=body.get("active_sessions"),
            response_time_ms=elapsed,
        )

    # ── Cache (Redis) ─────────────────────────────────────────────────────────

    @staticmethod
    def _cache_key(agent_id: str) -> str:
        return f"{HEALTH_CACHE_PREFIX}:{agent_id}"

    async def get_cached(self, agent_id: str) -> dict[str, Any] | None:
        redis = await get_redis()
        raw = await redis.get(self._cache_key(agent_id))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (ValueError, json.JSONDecodeError):
            return None

    async def set_cached(
        self,
        agent_id: str,
        result: HealthCheckResult,
        consecutive_failures: int,
    ) -> None:
        redis = await get_redis()
        payload = {
            "healthy": result.healthy,
            "ready": result.ready,
            "status": result.status,
            "reason": result.reason,
            "consecutive_failures": consecutive_failures,
            "checked_at": datetime.now(UTC).isoformat(),
            "agent_version": result.agent_version,
        }
        await redis.set(
            self._cache_key(agent_id),
            json.dumps(payload),
            ex=HEALTH_CACHE_TTL,
        )

    async def is_healthy_from_cache(self, agent_id: str) -> bool | None:
        """
        Returns True/False if cached, None if no cache entry exists.
        None means the caller should do a live check.
        """
        cached = await self.get_cached(agent_id)
        if cached is None:
            return None
        return cached.get("healthy", False) and cached.get("ready", False)
