from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.auth.jwt import AccessTokenExpiredError, InvalidAccessTokenError, decode_access_token
from app.models.users import User, UserStatus
from app.repositories.user_repo import UserRepository
from app.services.api_key_service import ApiKeyRateLimitError, ApiKeyService

_bearer = HTTPBearer(auto_error=False)


async def get_caller_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_api_key: str | None = Header(None, alias="x-api-key"),
    db: AsyncSession = Depends(get_session),
) -> User:
    """
    Resolves the authenticated caller from either:
      - A Bearer JWT access token  (our own frontend / marketplace users)
      - An x-api-key header        (external user agent applications)
    """
    user: User | None = None

    if credentials:
        user = await _user_from_jwt(credentials.credentials, db)
    elif x_api_key:
        user = await _user_from_api_key(x_api_key, db, request)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token or x-api-key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active.",
        )

    return user


async def _user_from_jwt(token: str, db: AsyncSession) -> User | None:
    try:
        payload = decode_access_token(token)
    except (AccessTokenExpiredError, InvalidAccessTokenError):
        return None

    repo = UserRepository(db)
    import uuid

    return await repo.get_by_id(uuid.UUID(payload.sub))


async def _user_from_api_key(raw_key: str, db: AsyncSession, request: Request) -> User | None:
    try:
        return await ApiKeyService(db).get_user_from_key(
            raw_key,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ApiKeyRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
