from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.users import User


class ApiKeyEnvironment(enum.StrEnum):
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"


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

    # First 8 characters of the raw key stored in plain text for display
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)

    # bcrypt hash of the full key — never stored in plain text after creation
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    environment: Mapped[ApiKeyEnvironment] = mapped_column(
        SAEnum(ApiKeyEnvironment, name="api_key_environment", create_type=True),
        default=ApiKeyEnvironment.SANDBOX,
        nullable=False,
    )

    # JSON array of permission strings, e.g. ["sessions:write", "agents:read"]
    permissions: Mapped[list[Any]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )

    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id} prefix={self.key_prefix} env={self.environment}>"


__all__ = ["ApiKey", "ApiKeyEnvironment"]
