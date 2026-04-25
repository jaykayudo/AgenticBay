from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from app.agents.user_agent.agent import MarketplaceUserAgent
from app.agents.user_agent.types import AgentState
from app.agents.user_agent.ws_clients.user_client import UserWSClient
from app.auth.session_token import (
    ChatSessionTokenError,
    decode_chat_session_token,
)
from app.core.database import AsyncSessionLocal
from app.models.sessions import Session, SessionPhase

logger = logging.getLogger(__name__)
router = APIRouter()

# session_id → active agent instance
_active_agents: dict[str, MarketplaceUserAgent] = {}


@router.websocket("/ws/user-agent/{session_id}")
async def user_agent_chat(websocket: WebSocket, session_id: str) -> None:
    """
    Frontend chat WebSocket for the marketplace user agent.

    Authentication: ?token=<chat_session_token>  (from POST /api/sessions)
    The session must have been created via POST /api/sessions first.

    Protocol:
      Inbound:  USER_MESSAGE | MODAL_RESPONSE | CANCEL_SESSION
      Outbound: AGENT_MESSAGE | PAYMENT_CONFIRMATION_MODAL | USER_PROMPT_MODAL | SESSION_COMPLETE
    """
    token = websocket.query_params.get("token")
    user_id = _authenticate(token, session_id)
    if user_id is None:
        await websocket.close(code=4001)
        return

    # Verify session exists in DB and is open
    if not await _session_is_valid(session_id):
        await websocket.close(code=4004)
        return

    await websocket.accept()
    user_ws = UserWSClient(websocket)
    agent = MarketplaceUserAgent(session_id=session_id, user_id=user_id)
    _active_agents[session_id] = agent

    try:
        while True:
            raw = await websocket.receive_json()
            msg_type: str = raw.get("type", "")
            data: dict = raw.get("data", {})

            if msg_type == "USER_MESSAGE":
                message_text: str = data.get("message", "")
                if agent.state == AgentState.IDLE:
                    await agent.start(user_ws, message_text)
                else:
                    await agent.handle_user_message(message_text)

            elif msg_type == "MODAL_RESPONSE":
                await agent.handle_user_response(data)

            elif msg_type == "CANCEL_SESSION":
                await agent.close("Session cancelled by user")
                break

            else:
                logger.warning("[%s] Unknown frontend message type: %s", session_id, msg_type)

    except WebSocketDisconnect:
        logger.info("[%s] User WS disconnected", session_id)
    except Exception:
        logger.exception("[%s] User WS error", session_id)
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011)
    finally:
        _active_agents.pop(session_id, None)
        if agent.state not in (AgentState.CLOSED, AgentState.CLOSING):
            await agent.close("Connection closed")


def _authenticate(token: str | None, session_id: str) -> str | None:
    """
    Decodes the chat session token and verifies it matches the requested session_id.
    Returns user_id on success, None on any failure.
    """
    if not token:
        return None
    try:
        payload = decode_chat_session_token(token)
    except ChatSessionTokenError:
        return None

    # Ensure the token was issued for this exact session
    if payload.session_id != session_id:
        return None

    return payload.sub


async def _session_is_valid(session_id: str) -> bool:
    """Returns True if the session exists in DB and has not been closed."""
    try:
        async with AsyncSessionLocal() as db:
            session = await db.get(Session, uuid.UUID(session_id))
    except Exception:
        return False

    return session is not None and session.phase != SessionPhase.CLOSED
