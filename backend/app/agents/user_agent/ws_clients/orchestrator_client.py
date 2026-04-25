from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import websockets
from jose import jwt

from app.agents.orchestrator.schema import JobSessionState, SessionPhase
from app.agents.orchestrator.session_store import SessionStore
from app.core.config import settings

if TYPE_CHECKING:
    from app.agents.user_agent.agent import MarketplaceUserAgent

logger = logging.getLogger(__name__)


class OrchestratorWSClient:
    """
    Connects to the marketplace orchestrator as a user agent.

    The user agent creates the orchestrator job session directly (bypassing
    the external HTTP start-job-session endpoint), then dials into the
    orchestrator WS as if it were a regular external user agent.
    """

    def __init__(self, agent: MarketplaceUserAgent) -> None:
        self.agent = agent
        self.ws: websockets.WebSocketClientProtocol | None = None
        self._running = False
        self.job_session_id: str | None = None
        self._job_token: str | None = None

    async def start_and_connect(self) -> None:
        """
        1. Create a JobSessionState in Redis (so orchestrator can find it)
        2. Issue a JWT for this session
        3. Open WS to /ws/user/{job_session_id}?token={token}
        4. Start listener task
        """
        job_session_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        token: str = jwt.encode(
            {"session_id": job_session_id},
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

        state = JobSessionState(
            session_id=job_session_id,
            user_id=self.agent.user_id,
            phase=SessionPhase.STARTED,
            auth_token=token,
            created_at=now,
            last_activity_at=now,
        )
        store = SessionStore()
        await store.save(state)

        self.job_session_id = job_session_id
        self._job_token = token
        self.agent.job_session_id = job_session_id

        ws_base = settings.ORCHESTRATOR_WS_URL.rstrip("/")
        ws_url = f"{ws_base}/ws/user/{job_session_id}?token={token}"

        logger.info("[%s] Connecting to orchestrator at %s", self.agent.session_id, ws_url)
        self.ws = await websockets.connect(ws_url)
        self._running = True
        logger.info(
            "[%s] Connected to orchestrator (job_session=%s)", self.agent.session_id, job_session_id
        )

        asyncio.create_task(self._listen())

    async def _listen(self) -> None:
        try:
            async for raw in self.ws:  # type: ignore[union-attr]
                message = json.loads(str(raw))
                await self.agent.handle_orchestrator_message(message)
        except websockets.ConnectionClosed:
            logger.info("[%s] Orchestrator WS closed", self.agent.session_id)
        except Exception:
            logger.exception("[%s] Orchestrator WS error", self.agent.session_id)
        finally:
            self._running = False

    async def send(self, payload: dict[str, Any]) -> None:
        if self.ws and self._running:
            await self.ws.send(json.dumps(payload))

    async def close(self) -> None:
        self._running = False
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
