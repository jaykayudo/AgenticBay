from __future__ import annotations

import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.users import User


class TransactionType(enum.StrEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    JOB_PAYMENT = "JOB_PAYMENT"
    FEE = "FEE"
    REFUND = "REFUND"
    EARNING = "EARNING"


class TransactionStatus(enum.StrEnum):
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class EscrowWallet(BaseModel):
    """Circle-managed escrow wallet pool entry. One row per wallet in the pool."""

    __tablename__ = "escrow_wallets"

    circle_wallet_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    wallet_address: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Locked while a job is in progress; released on CLOSE or refund
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    locked_by_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Last known balance in USDC (synced via Circle webhook)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=6), default=Decimal("0"), nullable=False
    )

    def __repr__(self) -> str:
        return f"<EscrowWallet id={self.id} address={self.wallet_address} locked={self.is_locked}>"


class WalletTransaction(BaseModel):
    """Full ledger of every USDC movement for a user account."""

    __tablename__ = "wallet_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, name="transaction_type", create_type=True),
        nullable=False,
    )

    # Amount in USDC with 6 decimal places
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USDC", nullable=False)

    status: Mapped[TransactionStatus] = mapped_column(
        SAEnum(TransactionStatus, name="transaction_status", create_type=True),
        default=TransactionStatus.INITIATED,
        nullable=False,
    )

    # Circle transfer ID (present for Circle-initiated transfers)
    circle_transfer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # On-chain transaction hash (present for blockchain transactions)
    onchain_tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    from_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Arbitrary context (job_id, invoice_id, agent_id, etc.)
    # Named tx_metadata to avoid conflict with SQLAlchemy's reserved Base.metadata
    tx_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}", nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="wallet_transactions")

    def __repr__(self) -> str:
        return (
            f"<WalletTransaction id={self.id} type={self.transaction_type}"
            f" amount={self.amount} status={self.status}>"
        )


__all__ = ["EscrowWallet", "WalletTransaction", "TransactionType", "TransactionStatus"]
