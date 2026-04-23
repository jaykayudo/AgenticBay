from __future__ import annotations

import enum
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.api_keys import ApiKey
    from app.models.auth import AuthSession, UserAuthProvider
    from app.models.wallets import WalletTransaction


class UserRole(enum.StrEnum):
    BUYER = "BUYER"
    AGENT_OWNER = "AGENT_OWNER"
    BOTH = "BOTH"
    ADMIN = "ADMIN"


class UserStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    BANNED = "BANNED"
    PENDING = "PENDING"


class User(BaseModel):
    __tablename__ = "users"

    # Identity
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, nullable=True)

    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Role and status
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", create_type=True),
        default=UserRole.BUYER,
        nullable=False,
    )
    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, name="user_status", create_type=True),
        default=UserStatus.ACTIVE,
        nullable=False,
    )

    # Verification
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    kyc_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Circle developer-controlled wallet (created on first payment activity)
    circle_wallet_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    wallet_address: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )

    # Spend controls (USDC, 6 decimal places)
    per_job_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=6), nullable=True
    )
    daily_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=6), nullable=True
    )
    confirm_above: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=20, scale=6), nullable=True
    )

    # Notification preferences stored as flexible JSON
    notification_preferences: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )

    # Relationships
    api_keys: Mapped[list[ApiKey]] = relationship(
        "ApiKey", back_populates="user", cascade="all, delete-orphan"
    )
    wallet_transactions: Mapped[list[WalletTransaction]] = relationship(
        "WalletTransaction", back_populates="user", cascade="all, delete-orphan"
    )
    auth_providers: Mapped[list[UserAuthProvider]] = relationship(
        "UserAuthProvider", back_populates="user", cascade="all, delete-orphan"
    )
    auth_sessions: Mapped[list[AuthSession]] = relationship(
        "AuthSession", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


__all__ = ["User", "UserRole", "UserStatus"]
