from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.users import User


class AuthProviderType(enum.StrEnum):
    GOOGLE = "GOOGLE"
    FACEBOOK = "FACEBOOK"
    EMAIL = "EMAIL"


class UserAuthProvider(BaseModel):
    __tablename__ = "user_auth_providers"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_auth_provider_user_provider"),
        UniqueConstraint("provider", "provider_user_id", name="uq_auth_provider_provider_uid"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[AuthProviderType] = mapped_column(
        SAEnum(AuthProviderType, name="auth_provider_type", create_type=True),
        nullable=False,
    )

    # Provider-issued user identifier (sub for Google, id for Facebook, email for EMAIL)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Email as returned by the provider (may differ from User.email)
    provider_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Raw profile data from the provider (tokens, profile picture URL, etc.)
    provider_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="auth_providers")

    def __repr__(self) -> str:
        return f"<UserAuthProvider id={self.id} provider={self.provider} user_id={self.user_id}>"


class AuthSession(BaseModel):
    __tablename__ = "auth_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Short plain-text prefix stored for fast lookup (e.g. first 8 chars of the token)
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    # bcrypt hash of the full refresh token
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Optional device/client metadata
    device_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="auth_sessions")

    def __repr__(self) -> str:
        return f"<AuthSession id={self.id} user_id={self.user_id} active={self.is_active}>"


__all__ = ["AuthProviderType", "UserAuthProvider", "AuthSession"]
