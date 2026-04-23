from __future__ import annotations

import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class SessionConnectionManager:
    """
    Manages exactly two WebSocket connections per job session:

      user    — the user agent that initiated the session
      service — the service agent that was hired to perform the job

    Both sides communicate exclusively through the orchestrator.
    Messages are never forwarded directly between the two; the orchestrator
    reads from one side, acts on the message, and writes to the other.
    """

    def __init__(self) -> None:
        # session_id → WebSocket
        self._user: dict[str, WebSocket] = {}
        self._service: dict[str, WebSocket] = {}

    # ── connection lifecycle ───────────────────────────────────────────────────

    async def connect_user(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._user[session_id] = ws
        logger.info("user-ws connected  session=%s", session_id)

    async def connect_service(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._service[session_id] = ws
        logger.info("service-ws connected  session=%s", session_id)

    def disconnect_user(self, session_id: str) -> None:
        self._user.pop(session_id, None)
        logger.info("user-ws disconnected  session=%s", session_id)

    def disconnect_service(self, session_id: str) -> None:
        self._service.pop(session_id, None)
        logger.info("service-ws disconnected  session=%s", session_id)

    def disconnect_all(self, session_id: str) -> None:
        self.disconnect_user(session_id)
        self.disconnect_service(session_id)

    # ── send ──────────────────────────────────────────────────────────────────

    async def send_to_user(self, session_id: str, data: str) -> None:
        ws = self._user.get(session_id)
        if ws is None:
            logger.warning("send_to_user: no user connection for session=%s", session_id)
            return
        try:
            await ws.send_text(data)
        except Exception as exc:
            logger.error("send_to_user error session=%s: %s", session_id, exc)
            self.disconnect_user(session_id)

    async def send_to_service(self, session_id: str, data: str) -> None:
        ws = self._service.get(session_id)
        if ws is None:
            logger.warning("send_to_service: no service connection for session=%s", session_id)
            return
        try:
            await ws.send_text(data)
        except Exception as exc:
            logger.error("send_to_service error session=%s: %s", session_id, exc)
            self.disconnect_service(session_id)

    # ── introspection ─────────────────────────────────────────────────────────

    def is_user_connected(self, session_id: str) -> bool:
        return session_id in self._user

    def is_service_connected(self, session_id: str) -> bool:
        return session_id in self._service

    @property
    def active_sessions(self) -> int:
        return len(self._user)


# Singleton shared by the WebSocket router and the orchestrator agent
session_manager = SessionConnectionManager()
