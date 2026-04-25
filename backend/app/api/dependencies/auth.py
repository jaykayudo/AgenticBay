from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.auth.jwt import (
    AccessTokenExpiredError,
    AccessTokenPayload,
    InvalidAccessTokenError,
    decode_access_token,
)
from app.models.users import User, UserStatus

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_access_token(token: str = Depends(oauth2_scheme)) -> AccessTokenPayload:
    try:
        return decode_access_token(token)
    except AccessTokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InvalidAccessTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    token: AccessTokenPayload = Depends(get_current_access_token),
    db: AsyncSession = Depends(get_session),
) -> User:
    try:
        user_id = UUID(token.sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token subject is invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await db.get(User, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current user could not be found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
