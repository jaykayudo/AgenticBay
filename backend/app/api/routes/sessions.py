from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.caller import get_caller_user
from app.api.deps import get_session
from app.auth.session_token import create_chat_session_token
from app.models.sessions import ConnectionType, Session, SessionPhase
from app.models.users import User

router = APIRouter(prefix="/sessions", tags=["sessions"])


class StartSessionResponse(BaseModel):
    session_id: str
    token: str
    ws_url: str


@router.post("", response_model=StartSessionResponse, status_code=201)
async def start_session(
    request: Request,
    user: User = Depends(get_caller_user),
    db: AsyncSession = Depends(get_session),
) -> StartSessionResponse:
    """
    Create a new user-agent chat session.

    Returns a short-lived session token (5 min) to authenticate the WebSocket
    connection. Connect to ws_url immediately after receiving this response.

    Auth: Bearer <access_token>  OR  x-api-key: <api_key>
    """
    session_id = uuid.uuid4()
    token = create_chat_session_token(
        user_id=str(user.id),
        session_id=str(session_id),
    )

    session = Session(
        id=session_id,
        user_id=user.id,
        phase=SessionPhase.STARTED,
        connection_type=ConnectionType.WEBSOCKET,
        job_session_auth_token=token,
    )
    db.add(session)
    await db.commit()

    ws_url = _build_ws_url(request, str(session_id), token)
    return StartSessionResponse(
        session_id=str(session_id),
        token=token,
        ws_url=ws_url,
    )


def _build_ws_url(request: Request, session_id: str, token: str) -> str:
    base = str(request.base_url).rstrip("/")
    # Replace http(s) scheme with ws(s) for the WebSocket URL
    if base.startswith("https://"):
        base = "wss://" + base[len("https://") :]
    else:
        base = "ws://" + base[len("http://") :]
    return f"{base}/ws/user-agent/{session_id}?token={token}"
