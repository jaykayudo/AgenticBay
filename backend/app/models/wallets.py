from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.invoices import Invoice
    from app.models.users import User


class EscrowWalletStatus(enum.StrEnum):
    AVAILABLE = "AVAILABLE"  # empty, ready to be assigned
    LOCKED = "LOCKED"  # assigned to an active invoice
    DRAINING = "DRAINING"  # currently being emptied
    MAINTENANCE = "MAINTENANCE"  # removed from pool manually


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
    """Circle-managed escrow wallet pool. One row per wallet in the pool."""

    __tablename__ = "escrow_wallets"

    circle_wallet_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    circle_wallet_set_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    wallet_address: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    blockchain: Mapped[str] = mapped_column(String(50), default="ARB-SEPOLIA", nullable=False)

    status: Mapped[EscrowWalletStatus] = mapped_column(
        SAEnum(EscrowWalletStatus, name="escrow_wallet_status", create_type=True),
        default=EscrowWalletStatus.AVAILABLE,
        nullable=False,
        index=True,
    )

    # UUID of the Invoice this wallet is locked to (no FK — avoids circular reference)
    locked_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )

    current_balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=6), default=Decimal("0"), nullable=False
    )
    last_balance_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_lifetime_volume: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=6), default=Decimal("0"), nullable=False
    )
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Back-reference: all invoices that have used this wallet
    invoices: Mapped[list[Invoice]] = relationship(
        "Invoice", foreign_keys="[Invoice.escrow_wallet_id]", back_populates="escrow_wallet"
    )

    def __repr__(self) -> str:
        return f"<EscrowWallet id={self.id} address={self.wallet_address} status={self.status}>"


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

    amount: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=6), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USDC", nullable=False)

    status: Mapped[TransactionStatus] = mapped_column(
        SAEnum(TransactionStatus, name="transaction_status", create_type=True),
        default=TransactionStatus.INITIATED,
        nullable=False,
    )

    circle_transfer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    onchain_tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    from_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    tx_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, server_default="{}", nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="wallet_transactions")

    def __repr__(self) -> str:
        return (
            f"<WalletTransaction id={self.id} type={self.transaction_type}"
            f" amount={self.amount} status={self.status}>"
        )


__all__ = [
    "EscrowWallet",
    "EscrowWalletStatus",
    "WalletTransaction",
    "TransactionType",
    "TransactionStatus",
]
