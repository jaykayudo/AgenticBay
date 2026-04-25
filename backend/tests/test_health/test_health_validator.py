"""
Tests for /health check validation during agent onboarding.
Covers: healthy, degraded, unhealthy, timeout, connection refused, non-JSON, invalid status.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.health_client import AgentHealthClient, HealthCheckResult
from app.services.agent_validator import AgentValidationError, AgentValidator


# ── HealthCheckResult helpers ─────────────────────────────────────────────────

def _mock_response(status_code: int = 200, body: dict | None = None, text: str | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    if body is not None:
        resp.json.return_value = body
    elif text is not None:
        resp.json.side_effect = ValueError("not JSON")
    return resp


# ── AgentHealthClient unit tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_client_ok_response() -> None:
    body = {"status": "ok", "ready": True, "version": "1.2.3", "active_sessions": 2}
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, body))

        result = await AgentHealthClient().check("http://agent.local")

    assert result.healthy is True
    assert result.ready is True
    assert result.status == "ok"
    assert result.agent_version == "1.2.3"
    assert result.active_sessions == 2
    assert result.reason is None


@pytest.mark.asyncio
async def test_health_client_degraded_response() -> None:
    body = {"status": "degraded", "ready": True, "reason": "LLM provider slow"}
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, body))

        result = await AgentHealthClient().check("http://agent.local")

    assert result.healthy is True   # degraded is still "healthy" (known status)
    assert result.ready is True
    assert result.status == "degraded"
    assert result.reason == "LLM provider slow"


@pytest.mark.asyncio
async def test_health_client_ready_false() -> None:
    body = {"status": "ok", "ready": False, "reason": "warming up"}
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, body))

        result = await AgentHealthClient().check("http://agent.local")

    assert result.healthy is True
    assert result.ready is False


@pytest.mark.asyncio
async def test_health_client_non_200_status() -> None:
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(503))

        result = await AgentHealthClient().check("http://agent.local")

    assert result.healthy is False
    assert result.ready is False
    assert result.status == "unreachable"
    assert "503" in (result.reason or "")


@pytest.mark.asyncio
async def test_health_client_timeout() -> None:
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))

        result = await AgentHealthClient().check("http://agent.local")

    assert result.healthy is False
    assert result.status == "unreachable"
    assert "timed out" in (result.reason or "").lower() or "3 second" in (result.reason or "")


@pytest.mark.asyncio
async def test_health_client_connection_refused() -> None:
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))

        result = await AgentHealthClient().check("http://agent.local")

    assert result.healthy is False
    assert result.status == "unreachable"
    assert result.reason is not None


@pytest.mark.asyncio
async def test_health_client_non_json_response() -> None:
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, text="not json"))

        result = await AgentHealthClient().check("http://agent.local")

    assert result.healthy is False
    assert "JSON" in (result.reason or "")


@pytest.mark.asyncio
async def test_health_client_invalid_status_value() -> None:
    body = {"status": "flying", "ready": True}
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=_mock_response(200, body))

        result = await AgentHealthClient().check("http://agent.local")

    assert result.healthy is False
    assert "flying" in (result.reason or "")


# ── AgentValidator integration tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_validator_fails_fast_on_unhealthy_agent() -> None:
    """Validator raises immediately if /health fails; /capabilities is never called."""
    validator = AgentValidator()
    unhealthy = HealthCheckResult(
        healthy=False, ready=False, status="unreachable",
        reason="Connection refused", agent_version=None,
        active_sessions=None, response_time_ms=3000.0,
    )

    with patch.object(validator._health_client, "check", return_value=unhealthy):
        with pytest.raises(AgentValidationError) as exc_info:
            await validator.validate("http://agent.local")

    assert "health" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_validator_fails_on_ready_false() -> None:
    validator = AgentValidator()
    not_ready = HealthCheckResult(
        healthy=True, ready=False, status="ok",
        reason=None, agent_version=None,
        active_sessions=None, response_time_ms=50.0,
    )

    with patch.object(validator._health_client, "check", return_value=not_ready):
        with pytest.raises(AgentValidationError) as exc_info:
            await validator.validate("http://agent.local")

    assert "ready=false" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_validator_includes_health_in_result() -> None:
    """Successful validation result contains the HealthCheckResult."""
    validator = AgentValidator()
    healthy = HealthCheckResult(
        healthy=True, ready=True, status="ok",
        reason=None, agent_version="2.0.0",
        active_sessions=1, response_time_ms=42.0,
    )

    cap_payload = {"message": "I can summarize documents."}
    invoke_payload = {"ok": True}

    with (
        patch.object(validator._health_client, "check", return_value=healthy),
        patch.object(validator, "_validate_capabilities", return_value=cap_payload),
        patch.object(validator, "_validate_invoke", return_value=invoke_payload),
    ):
        result = await validator.validate("http://agent.local")

    assert result.health.agent_version == "2.0.0"
    assert result.health.healthy is True
    assert result.capabilities == cap_payload
