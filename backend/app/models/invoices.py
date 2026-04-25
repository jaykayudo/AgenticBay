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
    from app.models.users import User
    from app.models.wallets import EscrowWallet


class InvoiceStatus(enum.StrEnum):
    PENDING = "PENDING"  # created, awaiting payment
    PAYMENT_CHECKING = "PAYMENT_CHECKING"  # verifying receipt
    PENDING_RELEASE = "PENDING_RELEASE"  # paid, awaiting job completion
    DISBURSING = "DISBURSING"  # disbursement in progress
    DISBURSED = "DISBURSED"  # funds released
    REFUNDED = "REFUNDED"  # refunded to payer
    EXPIRED = "EXPIRED"  # unpaid and past expiry
    FAILED = "FAILED"  # any unrecoverable failure


class Invoice(BaseModel):
    __tablename__ = "invoices"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    payer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    service_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Nullable until acquire_wallet assigns one
    escrow_wallet_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("escrow_wallets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Financials
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=6), nullable=False)
    marketplace_fee: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=6), nullable=False)
    agent_payout: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=6), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USDC", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus, name="invoice_status", create_type=True),
        default=InvoiceStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Wallet addresses for the payment
    payer_wallet_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payee_wallet_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marketplace_wallet_address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamps
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disbursed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Payment transaction (user → escrow)
    payment_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_tx_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Agent disbursement transaction (escrow → agent)
    agent_disbursement_tx_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_disbursement_tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Marketplace fee transaction (escrow → marketplace)
    fee_disbursement_tx_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fee_disbursement_tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Refund transaction (escrow → payer)
    refund_tx_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    refund_tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    job: Mapped[Job] = relationship("Job", back_populates="invoice")
    payer_user: Mapped[User] = relationship("User", foreign_keys=[payer_user_id])
    service_agent: Mapped[Agent] = relationship("Agent", foreign_keys=[service_agent_id])
    escrow_wallet: Mapped[EscrowWallet | None] = relationship(
        "EscrowWallet", foreign_keys=[escrow_wallet_id], back_populates="invoices"
    )

    def __repr__(self) -> str:
        return (
            f"<Invoice id={self.id} status={self.status} amount={self.amount} job_id={self.job_id}>"
        )


__all__ = ["Invoice", "InvoiceStatus"]
