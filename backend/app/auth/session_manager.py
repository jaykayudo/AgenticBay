from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.jwt import create_access_token
from app.core.config import settings
from app.models.auth_session import AuthSession
from app.models.users import User, UserStatus


class SessionManagerError(Exception):
    """Base exception for session management failures."""


class InvalidRefreshTokenError(SessionManagerError):
    """Raised when a refresh token is invalid, expired, or revoked."""


class RefreshTokenReuseDetectedError(SessionManagerError):
    """Raised when an inactive refresh token is presented again."""


@dataclass(slots=True)
class IssuedTokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    session: AuthSession


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize_optional_text(value: str | None, *, limit: int) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:limit]


def _build_refresh_token() -> tuple[str, str, str]:
    token_body = secrets.token_urlsafe(32)
    token = f"rt_{token_body}"
    token_prefix = f"rt_{token_body[:8]}..."
    token_hash = hashlib.sha256(f"{settings.SECRET_KEY}:{token}".encode()).hexdigest()
    return token, token_prefix, token_hash


class SessionManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def issue_tokens(
        self,
        *,
        user: User,
        device_info: str | None,
        ip_address: str | None,
        rotated_from_session_id: UUID | None = None,
    ) -> IssuedTokenPair:
        now = _now()
        refresh_token, refresh_token_prefix, refresh_token_hash = _build_refresh_token()
        session = AuthSession(
            user_id=user.id,
            refresh_token_hash=refresh_token_hash,
            refresh_token_prefix=refresh_token_prefix,
            device_info=_normalize_optional_text(device_info, limit=2048),
            ip_address=_normalize_optional_text(ip_address, limit=45),
            expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            last_used_at=now,
            is_active=True,
            rotated_from_session_id=rotated_from_session_id,
        )
        self.db.add(session)
        await self.db.flush()

        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
            session_id=session.id,
        )

        return IssuedTokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
            session=session,
        )

    async def refresh_tokens(
        self,
        *,
        refresh_token: str,
        device_info: str | None,
        ip_address: str | None,
    ) -> IssuedTokenPair:
        session = await self._get_session_by_refresh_token(refresh_token, for_update=True)
        now = _now()

        if session is None:
            raise InvalidRefreshTokenError("Refresh token is invalid.")
        if not session.is_active:
            await self.revoke_all_user_sessions(
                session.user_id,
                reason="reuse_detected",
                revoked_at=now,
            )
            raise RefreshTokenReuseDetectedError(
                "Refresh token reuse detected. All sessions have been invalidated."
            )
        if session.expires_at <= now:
            self._revoke_session(session, reason="expired", revoked_at=now)
            raise InvalidRefreshTokenError("Refresh token has expired.")

        user = session.user
        if user is None or user.status != UserStatus.ACTIVE:
            self._revoke_session(session, reason="user_inactive", revoked_at=now)
            raise InvalidRefreshTokenError("User is inactive.")

        self._revoke_session(session, reason="rotated", revoked_at=now)

        return await self.issue_tokens(
            user=user,
            device_info=device_info or session.device_info,
            ip_address=ip_address or session.ip_address,
            rotated_from_session_id=session.id,
        )

    async def revoke_by_refresh_token(self, refresh_token: str) -> AuthSession:
        session = await self._get_session_by_refresh_token(refresh_token, for_update=True)
        now = _now()

        if session is None:
            raise InvalidRefreshTokenError("Refresh token is invalid.")
        if not session.is_active:
            raise InvalidRefreshTokenError("Refresh token has already been revoked.")
        if session.expires_at <= now:
            self._revoke_session(session, reason="expired", revoked_at=now)
            raise InvalidRefreshTokenError("Refresh token has expired.")

        self._revoke_session(session, reason="logout", revoked_at=now)
        return session

    async def revoke_all_user_sessions(
        self,
        user_id: UUID | str,
        *,
        reason: str,
        revoked_at: datetime | None = None,
    ) -> int:
        now = revoked_at or _now()
        result = await self.db.scalars(
            select(AuthSession).where(
                AuthSession.user_id == user_id,
                AuthSession.is_active.is_(True),
            )
        )
        sessions = list(result)
        for session in sessions:
            self._revoke_session(session, reason=reason, revoked_at=now)
        return len(sessions)

    async def revoke_user_session(self, *, user_id: UUID | str, session_id: UUID | str) -> bool:
        session = await self.db.scalar(
            select(AuthSession).where(
                AuthSession.id == session_id,
                AuthSession.user_id == user_id,
            )
        )
        if session is None:
            return False
        if session.is_active:
            self._revoke_session(session, reason="session_revoked", revoked_at=_now())
        return True

    async def list_active_sessions(self, user_id: UUID | str) -> list[AuthSession]:
        result = await self.db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.is_active.is_(True),
                AuthSession.expires_at > _now(),
            )
            .order_by(AuthSession.last_used_at.desc(), AuthSession.created_at.desc())
        )
        return list(result)

    async def _get_session_by_refresh_token(
        self,
        refresh_token: str,
        *,
        for_update: bool,
    ) -> AuthSession | None:
        normalized = refresh_token.strip()
        if not normalized.startswith("rt_"):
            return None

        token_hash = hashlib.sha256(f"{settings.SECRET_KEY}:{normalized}".encode()).hexdigest()
        statement: Select[tuple[AuthSession]] = (
            select(AuthSession)
            .options(selectinload(AuthSession.user))
            .where(AuthSession.refresh_token_hash == token_hash)
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(AuthSession | None, await self.db.scalar(statement))

    @staticmethod
    def _revoke_session(session: AuthSession, *, reason: str, revoked_at: datetime) -> None:
        session.is_active = False
        session.revoked_at = revoked_at
        session.revoked_reason = reason
        session.last_used_at = revoked_at
