from __future__ import annotations

import json
import logging

import websockets

from .command_handlers import handle_command
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class OrchestratorWSClient:
    def __init__(
        self,
        session_id: str,
        token: str,
        orchestrator_ws_url: str,
        orchestrator_key: str,
        session_manager: SessionManager,
    ) -> None:
        self.session_id = session_id
        self.token = token
        self.base_url = orchestrator_ws_url
        self.orchestrator_key = orchestrator_key
        self.session_manager = session_manager
        self.ws: websockets.WebSocketClientProtocol | None = None
        self._running = False

    def _build_ws_url(self) -> str:
        return (
            f"{self.base_url}/ws/service/{self.session_id}"
            f"?token={self.token}&key={self.orchestrator_key}"
        )

    async def run(self) -> None:
        url = self._build_ws_url()
        logger.info("[%s] Connecting to orchestrator at %s", self.session_id, url)

        try:
            async with websockets.connect(url) as ws:
                self.ws = ws
                self._running = True
                logger.info("[%s] Connected to orchestrator", self.session_id)

                async for message in ws:
                    await self._handle_message(str(message))
        except Exception:
            logger.exception("[%s] WebSocket error", self.session_id)
        finally:
            self._running = False
            self.session_manager.remove(self.session_id)
            logger.info("[%s] WebSocket closed, session removed", self.session_id)

    async def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
            command = msg.get("command")
            arguments = msg.get("arguments", {})

            logger.info("[%s] Received command: %s", self.session_id, command)

            response = await handle_command(
                session_id=self.session_id,
                command=command,
                arguments=arguments,
                session_manager=self.session_manager,
            )

            if response:
                await self.send(response)

        except Exception:
            logger.exception("[%s] Error handling message", self.session_id)
            await self.send(
                {
                    "type": "ERROR",
                    "data": {"message": "Internal error processing command"},
                }
            )

    async def send(self, message: dict) -> None:
        if self.ws and self._running:
            await self.ws.send(json.dumps(message))
            logger.debug(
                "[%s] Sent: %s", self.session_id, message.get("type", "response")
            )
