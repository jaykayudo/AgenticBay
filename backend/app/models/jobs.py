from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.agents import Agent, AgentAction
    from app.models.invoices import Invoice
    from app.models.sessions import Session
    from app.models.users import User


class JobStatus(enum.StrEnum):
    AWAITING_INVOICE = "AWAITING_INVOICE"
    INVOICE_GENERATED = "INVOICE_GENERATED"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DISPUTED = "DISPUTED"
    REFUNDED = "REFUNDED"
    EXPIRED = "EXPIRED"


class Job(BaseModel):
    __tablename__ = "jobs"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # The specific action invoked; nullable when the request is free-form
    action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_actions.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[JobStatus] = mapped_column(
        SAEnum(JobStatus, name="job_status", create_type=True),
        default=JobStatus.AWAITING_INVOICE,
        nullable=False,
        index=True,
    )

    # Request lifecycle fields
    raw_user_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_interpretation: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    action_inputs: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    service_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    formatted_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Post-completion quality score (0.00–5.00)
    quality_score: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=3, scale=2), nullable=True
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    session: Mapped[Session] = relationship("Session", back_populates="jobs")
    buyer: Mapped[User] = relationship("User", foreign_keys=[buyer_id])
    agent: Mapped[Agent] = relationship("Agent", foreign_keys=[agent_id])
    action: Mapped[AgentAction | None] = relationship("AgentAction", foreign_keys=[action_id])
    # One-to-one with Invoice (uselist=False)
    invoice: Mapped[Invoice | None] = relationship("Invoice", back_populates="job", uselist=False)

    def __repr__(self) -> str:
        return f"<Job id={self.id} status={self.status} agent_id={self.agent_id}>"


__all__ = ["Job", "JobStatus"]
