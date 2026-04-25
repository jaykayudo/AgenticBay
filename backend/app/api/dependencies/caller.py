from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.auth.jwt import AccessTokenExpiredError, InvalidAccessTokenError, decode_access_token
from app.models.users import User, UserStatus
from app.repositories.api_key_repo import ApiKeyRepository
from app.repositories.user_repo import UserRepository

_bearer = HTTPBearer(auto_error=False)


async def get_caller_user(
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
        user = await _user_from_api_key(x_api_key, db)

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


async def _user_from_api_key(raw_key: str, db: AsyncSession) -> User | None:
    key_repo = ApiKeyRepository(db)
    api_key = await key_repo.validate_key(raw_key)
    if api_key is None:
        return None

    user_repo = UserRepository(db)
    return await user_repo.get_by_id(api_key.user_id)
