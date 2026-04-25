from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal, cast
from uuid import UUID

from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel, ValidationError

from app.core.config import settings


class JWTValidationError(Exception):
    """Base exception for access token validation errors."""


class AccessTokenExpiredError(JWTValidationError):
    """Raised when an access token has expired."""


class InvalidAccessTokenError(JWTValidationError):
    """Raised when an access token is malformed or cannot be verified."""


class AccessTokenPayload(BaseModel):
    sub: str
    email: str
    role: str
    type: Literal["access"]
    iat: int
    exp: int
    sid: str


def create_access_token(
    *,
    user_id: UUID | str,
    email: str,
    role: str,
    session_id: UUID | str,
    expires_in_seconds: int | None = None,
) -> str:
    issued_at = datetime.now(UTC)
    expires_in = expires_in_seconds or settings.ACCESS_TOKEN_EXPIRE_SECONDS
    expires_at = issued_at + timedelta(seconds=expires_in)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "sid": str(session_id),
    }
    return cast(str, jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM))


def decode_access_token(token: str) -> AccessTokenPayload:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except ExpiredSignatureError as exc:
        raise AccessTokenExpiredError("Access token has expired.") from exc
    except JWTError as exc:
        raise InvalidAccessTokenError("Access token is invalid.") from exc

    try:
        claims = AccessTokenPayload.model_validate(payload)
    except ValidationError as exc:
        raise InvalidAccessTokenError("Access token is invalid.") from exc

    if claims.type != "access":
        raise InvalidAccessTokenError("Token is not an access token.")

    return claims
