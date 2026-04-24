from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from app.agents.orchestrator.agent import OrchestratorAgent
from app.core.config import settings
from app.websocket.manager import session_manager

logger = logging.getLogger(__name__)
router = APIRouter()
orch = OrchestratorAgent()


# ── User agent WebSocket room ──────────────────────────────────────────────────


@router.websocket("/ws/user/{session_id}")
async def user_websocket(websocket: WebSocket, session_id: str) -> None:
    token = websocket.query_params.get("token")
    if not token or not _verify_session_token(session_id, token):
        await websocket.close(code=4001)
        return

    await session_manager.connect_user(session_id, websocket)

    async def send(text: str) -> None:
        await session_manager.send_to_user(session_id, text)

    try:
        while True:
            raw = await websocket.receive_text()
            logger.debug("[user %s] ← %s", session_id, raw)
            await orch.handle_message(session_id=session_id, raw_message=raw, send=send)
    except WebSocketDisconnect:
        logger.info("user-ws disconnected  session=%s", session_id)
    except Exception as exc:
        logger.error("user-ws error  session=%s: %s", session_id, exc)
        await websocket.close(code=1011)
    finally:
        session_manager.disconnect_user(session_id)


# ── Service agent WebSocket room ───────────────────────────────────────────────


@router.websocket("/ws/service/{session_id}")
async def service_websocket(websocket: WebSocket, session_id: str) -> None:
    token = websocket.query_params.get("token")
    key = websocket.query_params.get("key")

    # Both the session JWT and the per-agent orchestrator key are required
    if not token or not key:
        await websocket.close(code=4001)
        return

    if not _verify_session_token(session_id, token):
        await websocket.close(code=4001)
        return

    if not await _verify_orchestrator_key(session_id, key):
        await websocket.close(code=4003)
        return

    await session_manager.connect_service(session_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            logger.debug("[service %s] ← %s", session_id, raw)
            await orch.handle_service_message(session_id=session_id, raw=raw)
    except WebSocketDisconnect:
        logger.info("service-ws disconnected  session=%s", session_id)
    except Exception as exc:
        logger.error("service-ws error  session=%s: %s", session_id, exc)
        await websocket.close(code=1011)
    finally:
        session_manager.disconnect_service(session_id)


# ── Auth helpers ───────────────────────────────────────────────────────────────


def _verify_session_token(session_id: str, token: str) -> bool:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return bool(payload.get("session_id") == session_id)
    except (ExpiredSignatureError, JWTError):
        return False


async def _verify_orchestrator_key(session_id: str, key: str) -> bool:
    """Check that `key` matches the orchestrator_api_key stored in session state."""
    state = await orch.session_store.get(session_id)
    if not state:
        return False
    return state.agent_orchestrator_key == key
