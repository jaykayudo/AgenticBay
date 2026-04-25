from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

CHAT_SESSION_TOKEN_TTL_SECONDS = 300  # 5 minutes — only needed to establish the WS connection


class ChatSessionTokenError(Exception):
    pass


class ChatSessionTokenExpiredError(ChatSessionTokenError):
    pass


class ChatSessionTokenPayload(BaseModel):
    sub: str  # user_id
    session_id: str
    type: str  # always "chat_session"


def create_chat_session_token(*, user_id: str, session_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "session_id": session_id,
        "type": "chat_session",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=CHAT_SESSION_TOKEN_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_chat_session_token(token: str) -> ChatSessionTokenPayload:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except ExpiredSignatureError as exc:
        raise ChatSessionTokenExpiredError("Chat session token has expired.") from exc
    except JWTError as exc:
        raise ChatSessionTokenError("Chat session token is invalid.") from exc

    if payload.get("type") != "chat_session":
        raise ChatSessionTokenError("Token is not a chat session token.")

    return ChatSessionTokenPayload(
        sub=payload["sub"],
        session_id=payload["session_id"],
        type=payload["type"],
    )
