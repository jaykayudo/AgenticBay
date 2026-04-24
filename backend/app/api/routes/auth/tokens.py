from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_access_token, get_current_user
from app.api.deps import get_session
from app.auth.jwt import AccessTokenPayload
from app.auth.session_manager import (
    InvalidRefreshTokenError,
    RefreshTokenReuseDetectedError,
    SessionManager,
)
from app.models.users import User
from app.schemas.auth import (
    AuthSessionListResponse,
    AuthSessionRead,
    LogoutAllResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserProfileRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _request_metadata(request: Request) -> tuple[str | None, str | None]:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip_address = forwarded_for.split(",")[0].strip()
    elif request.client is not None:
        ip_address = request.client.host
    else:
        ip_address = None
    return request.headers.get("user-agent"), ip_address


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> TokenResponse:
    manager = SessionManager(db)
    device_info, ip_address = _request_metadata(request)

    try:
        tokens = await manager.refresh_tokens(
            refresh_token=payload.refresh_token,
            device_info=device_info,
            ip_address=ip_address,
        )
    except (InvalidRefreshTokenError, RefreshTokenReuseDetectedError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_session),
) -> Response:
    manager = SessionManager(db)
    try:
        await manager.revoke_by_refresh_token(payload.refresh_token)
    except InvalidRefreshTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout-all", response_model=LogoutAllResponse)
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> LogoutAllResponse:
    manager = SessionManager(db)
    revoked_sessions = await manager.revoke_all_user_sessions(
        current_user.id,
        reason="logout_all",
    )
    return LogoutAllResponse(revoked_sessions=revoked_sessions)


@router.get("/sessions", response_model=AuthSessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    token: AccessTokenPayload = Depends(get_current_access_token),
    db: AsyncSession = Depends(get_session),
) -> AuthSessionListResponse:
    manager = SessionManager(db)
    sessions = await manager.list_active_sessions(current_user.id)
    return AuthSessionListResponse(
        sessions=[
            AuthSessionRead(
                id=session.id,
                device_info=session.device_info,
                ip_address=session.ip_address,
                created_at=session.created_at,
                last_used_at=session.last_used_at,
                is_current=str(session.id) == token.sid,
            )
            for session in sessions
        ]
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    manager = SessionManager(db)
    revoked = await manager.revoke_user_session(user_id=current_user.id, session_id=session_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserProfileRead)
async def me(current_user: User = Depends(get_current_user)) -> UserProfileRead:
    return UserProfileRead.model_validate(current_user)
