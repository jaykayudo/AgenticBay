"""
Unit tests for OrchestratorAgent HTTP helper methods.

Both helpers use aiohttp.ClientSession as an async context manager, so we
mock that at the import point rather than using a live HTTP server.

_fetch_capabilities:
  - Returns message string on HTTP 200
  - Returns None on non-200 status
  - Returns None when "message" key is absent from response body
  - Returns None on network exception

_send_connect_request:
  - Returns True on HTTP 200
  - Returns False on non-200 status
  - Returns False on network exception
  - Posts the correct payload (session_id, token, orchestrator_ws_url, orchestrator_key)
  - Sets X-Orchestrator-Key header
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.test_orchestrator_agent.conftest import build_orchestrator

pytestmark = [pytest.mark.asyncio]


# ── aiohttp mock builder ──────────────────────────────────────────────────────


def _mock_http_session(status: int, json_body: dict | None = None) -> MagicMock:
    """
    Return a mock aiohttp.ClientSession that acts as an async context manager.
    Both the session and the response must support `async with` via explicit
    __aenter__/__aexit__ AsyncMocks — using AsyncMock() for the whole object
    makes .get()/.post() return coroutines, which break the inner `async with`.
    """
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_body or {})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    mock_session.post = MagicMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    return mock_session


def _network_error_session(exc: Exception) -> MagicMock:
    """Return a mock session whose get/post raises exc."""
    mock_session = MagicMock()
    mock_session.get = MagicMock(side_effect=exc)
    mock_session.post = MagicMock(side_effect=exc)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    return mock_session


# ═══════════════════════════════════════════════════════════════════════════════
# _fetch_capabilities
# ═══════════════════════════════════════════════════════════════════════════════


async def test_fetch_capabilities_returns_message_on_200() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(200, {"message": "I can do analysis and summarisation"})

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        result = await orch._fetch_capabilities("https://agent.example.com")

    assert result == "I can do analysis and summarisation"


async def test_fetch_capabilities_calls_correct_url() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(200, {"message": "caps"})

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        await orch._fetch_capabilities("https://agent.example.com")

    session.get.assert_called_once()
    called_url = session.get.call_args[0][0]
    assert called_url == "https://agent.example.com/capabilities"


async def test_fetch_capabilities_strips_trailing_slash_from_endpoint() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(200, {"message": "caps"})

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        await orch._fetch_capabilities("https://agent.example.com/")

    called_url = session.get.call_args[0][0]
    assert called_url == "https://agent.example.com/capabilities"


async def test_fetch_capabilities_returns_none_on_404() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(404)

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        result = await orch._fetch_capabilities("https://agent.example.com")

    assert result is None


async def test_fetch_capabilities_returns_none_on_500() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(500)

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        result = await orch._fetch_capabilities("https://agent.example.com")

    assert result is None


async def test_fetch_capabilities_returns_none_when_message_key_missing() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(200, {"status": "ok"})  # no "message" key

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        result = await orch._fetch_capabilities("https://agent.example.com")

    assert result is None


async def test_fetch_capabilities_returns_none_on_network_exception() -> None:
    orch = build_orchestrator()
    session = _network_error_session(ConnectionError("timeout"))

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        result = await orch._fetch_capabilities("https://agent.example.com")

    assert result is None


async def test_fetch_capabilities_converts_message_to_string() -> None:
    """Even if the body has a non-string message, it should be returned as str."""
    orch = build_orchestrator()
    session = _mock_http_session(200, {"message": 12345})

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        result = await orch._fetch_capabilities("https://agent.example.com")

    assert result == "12345"


# ═══════════════════════════════════════════════════════════════════════════════
# _send_connect_request
# ═══════════════════════════════════════════════════════════════════════════════


async def test_send_connect_request_returns_true_on_200() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(200)

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        result = await orch._send_connect_request(
            endpoint="https://agent.example.com",
            session_id="sess-123",
            token="jwt-token",
            orchestrator_key="orch-key",
        )

    assert result is True


async def test_send_connect_request_returns_false_on_500() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(500)

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        result = await orch._send_connect_request(
            endpoint="https://agent.example.com",
            session_id="sess-123",
            token="jwt-token",
            orchestrator_key="orch-key",
        )

    assert result is False


async def test_send_connect_request_returns_false_on_401() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(401)

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        result = await orch._send_connect_request(
            endpoint="https://agent.example.com",
            session_id="sess-123",
            token="jwt-token",
            orchestrator_key="orch-key",
        )

    assert result is False


async def test_send_connect_request_returns_false_on_network_exception() -> None:
    orch = build_orchestrator()
    session = _network_error_session(ConnectionRefusedError("refused"))

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        result = await orch._send_connect_request(
            endpoint="https://agent.example.com",
            session_id="sess-123",
            token="jwt-token",
            orchestrator_key="orch-key",
        )

    assert result is False


async def test_send_connect_request_posts_to_connect_endpoint() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(200)

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        await orch._send_connect_request(
            endpoint="https://agent.example.com",
            session_id="sess-abc",
            token="tok-xyz",
            orchestrator_key="key-123",
        )

    called_url = session.post.call_args[0][0]
    assert called_url == "https://agent.example.com/connect"


async def test_send_connect_request_strips_trailing_slash() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(200)

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        await orch._send_connect_request(
            endpoint="https://agent.example.com/",
            session_id="s",
            token="t",
            orchestrator_key="k",
        )

    called_url = session.post.call_args[0][0]
    assert called_url == "https://agent.example.com/connect"


async def test_send_connect_request_payload_contains_session_id_and_token() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(200)

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        await orch._send_connect_request(
            endpoint="https://agent.example.com",
            session_id="my-session-id",
            token="my-jwt-token",
            orchestrator_key="my-orch-key",
        )

    payload = session.post.call_args.kwargs.get("json") or session.post.call_args[1].get("json", {})
    assert payload["session_id"] == "my-session-id"
    assert payload["token"] == "my-jwt-token"
    assert payload["orchestrator_key"] == "my-orch-key"


async def test_send_connect_request_header_contains_orchestrator_key() -> None:
    orch = build_orchestrator()
    session = _mock_http_session(200)

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        await orch._send_connect_request(
            endpoint="https://agent.example.com",
            session_id="s",
            token="t",
            orchestrator_key="secret-orch-key",
        )

    headers = session.post.call_args.kwargs.get("headers") or session.post.call_args[1].get("headers", {})
    assert headers.get("X-Orchestrator-Key") == "secret-orch-key"


async def test_send_connect_request_payload_contains_orchestrator_ws_url() -> None:
    """The service agent needs the WS URL to dial back. It comes from settings."""
    orch = build_orchestrator()
    session = _mock_http_session(200)

    with patch("app.agents.orchestrator.agent.aiohttp.ClientSession", return_value=session):
        await orch._send_connect_request(
            endpoint="https://agent.example.com",
            session_id="s",
            token="t",
            orchestrator_key="k",
        )

    payload = session.post.call_args.kwargs.get("json") or session.post.call_args[1].get("json", {})
    # orchestrator_ws_url comes from settings.ORCHESTRATOR_WS_URL (default: ws://localhost:8000)
    assert "orchestrator_ws_url" in payload
