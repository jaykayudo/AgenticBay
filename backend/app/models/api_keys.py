from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.users import User


class ApiKeyEnvironment(enum.StrEnum):
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"


class ApiKeyPermission(enum.StrEnum):
    SEARCH = "search"
    HIRE = "hire"
    PAY = "pay"
    CHECK_BALANCE = "check_balance"
    READ_HISTORY = "read_history"


class ApiKeyAuditAction(enum.StrEnum):
    CREATED = "CREATED"
    USED = "USED"
    REVOKED = "REVOKED"
    ROTATED = "ROTATED"
    EXPIRED = "EXPIRED"


class ApiKey(BaseModel):
    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Human-readable label set by the user at creation time
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # First 16 characters of the raw key stored in plain text for display
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)

    # bcrypt hash of the full key — never stored in plain text after creation
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    environment: Mapped[ApiKeyEnvironment] = mapped_column(
        SAEnum(ApiKeyEnvironment, name="api_key_environment", create_type=True),
        default=ApiKeyEnvironment.SANDBOX,
        nullable=False,
    )

    # JSON array of ApiKeyPermission values
    permissions: Mapped[list[Any]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    last_used_user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="api_keys")
    audit_logs: Mapped[list[ApiKeyAuditLog]] = relationship(
        "ApiKeyAuditLog", back_populates="api_key", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id} prefix={self.key_prefix} env={self.environment}>"


class ApiKeyAuditLog(BaseModel):
    __tablename__ = "api_key_audit_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}", nullable=False
    )

    api_key: Mapped[ApiKey | None] = relationship("ApiKey", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<ApiKeyAuditLog key_id={self.key_id} action={self.action}>"


__all__ = [
    "ApiKey",
    "ApiKeyAuditLog",
    "ApiKeyAuditAction",
    "ApiKeyEnvironment",
    "ApiKeyPermission",
]
