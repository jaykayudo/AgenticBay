from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.users import User


class NotificationType(enum.StrEnum):
    JOB_STARTED = "JOB_STARTED"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"
    PAYMENT_SENT = "PAYMENT_SENT"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    INVOICE_GENERATED = "INVOICE_GENERATED"
    INVOICE_PAID = "INVOICE_PAID"
    DISPUTE_OPENED = "DISPUTE_OPENED"
    DISPUTE_RESOLVED = "DISPUTE_RESOLVED"
    AGENT_HIRED = "AGENT_HIRED"
    REVIEW_RECEIVED = "REVIEW_RECEIVED"
    LOW_BALANCE = "LOW_BALANCE"


class Notification(BaseModel):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    notification_type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, name="notification_type", create_type=True),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Arbitrary JSON payload for dynamic body rendering (job_id, agent_name, amount, etc.)
    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return (
            f"<Notification id={self.id} type={self.notification_type}"
            f" user_id={self.user_id} read={self.is_read}>"
        )


__all__ = ["Notification", "NotificationType"]
