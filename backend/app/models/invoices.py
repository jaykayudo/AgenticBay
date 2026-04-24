from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.agents import Agent
    from app.models.jobs import Job
    from app.models.sessions import Session
    from app.models.users import User


class InvoiceStatus(enum.StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    DISBURSED = "DISBURSED"
    REFUNDED = "REFUNDED"
    EXPIRED = "EXPIRED"


class Invoice(BaseModel):
    __tablename__ = "invoices"

    # One-to-one with Job
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
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

    # Amount in USDC with 6 decimal places
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USDC", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus, name="invoice_status", create_type=True),
        default=InvoiceStatus.PENDING,
        nullable=False,
        index=True,
    )

    # On-chain identity — bytes32 invoice ID stored as 0x-prefixed hex string
    onchain_invoice_id: Mapped[str | None] = mapped_column(
        String(66), unique=True, nullable=True, index=True
    )

    # The deployed escrow contract that holds funds for this invoice
    invoice_contract_address: Mapped[str | None] = mapped_column(String(42), nullable=True)

    # Function name the user agent must call on the contract to pay
    payment_function_name: Mapped[str] = mapped_column(
        String(100), default="pay_invoice", nullable=False
    )

    # On-chain transaction hashes — each step in the invoice lifecycle
    contract_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    payment_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    verification_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    disbursement_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    refund_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disbursed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    job: Mapped[Job] = relationship("Job", back_populates="invoice")
    session: Mapped[Session] = relationship("Session", foreign_keys=[session_id])
    buyer: Mapped[User] = relationship("User", foreign_keys=[buyer_id])
    agent: Mapped[Agent] = relationship("Agent", foreign_keys=[agent_id])

    def __repr__(self) -> str:
        return (
            f"<Invoice id={self.id} status={self.status} amount={self.amount} job_id={self.job_id}>"
        )


__all__ = ["Invoice", "InvoiceStatus"]
