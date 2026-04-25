from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.invoices import Invoice, InvoiceStatus
from app.models.jobs import Job
from app.models.notifications import Notification, NotificationType
from app.models.users import User
from app.models.wallets import TransactionStatus, TransactionType, WalletTransaction
from app.services.circle_client import CircleClient


class WalletServiceError(Exception):
    """Base wallet operation error."""


class WalletProvisionError(WalletServiceError):
    """Raised when a Circle wallet cannot be provisioned."""


class InsufficientBalanceError(WalletServiceError):
    """Raised when a withdrawal exceeds available live balance."""


class WalletTransactionNotFoundError(WalletServiceError):
    """Raised when a transaction cannot be found for the current user."""


class CircleWebhookSignatureError(WalletServiceError):
    """Raised when a Circle webhook signature fails verification."""


@dataclass(frozen=True)
class PaginationMeta:
    total: int
    page: int
    page_size: int
    has_next: bool


@dataclass(frozen=True)
class TransactionListResult:
    transactions: list[WalletTransaction]
    meta: PaginationMeta


class WalletService:
    def __init__(self, db: AsyncSession, *, circle: CircleClient | None = None) -> None:
        self.db = db
        self.circle = circle or CircleClient()

    async def ensure_user_wallet(self, user: User) -> User:
        if user.circle_wallet_id and user.wallet_address:
            return user

        wallet = await self.circle.create_developer_wallet(name=f"User Wallet {user.id}")
        wallet_id = str(wallet.get("id") or "")
        address = str(wallet.get("address") or "")
        if not wallet_id or not address:
            raise WalletProvisionError("Circle did not return a usable wallet.")

        user.circle_wallet_id = wallet_id
        user.wallet_address = address
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_live_balance(self, user: User) -> Decimal:
        user = await self.ensure_user_wallet(user)
        balance = Decimal(str(await self.circle.get_wallet_balance(str(user.circle_wallet_id))))
        await self._trigger_low_balance_notification(user, balance)
        return balance

    async def get_wallet_address(self, user: User) -> dict[str, str]:
        user = await self.ensure_user_wallet(user)
        address = str(user.wallet_address)
        blockchain = settings.BLOCKCHAIN
        return {
            "walletId": str(user.circle_wallet_id),
            "address": address,
            "blockchain": blockchain,
            "qrData": f"{blockchain}:{address}?asset=USDC",
        }

    async def initiate_deposit(self, user: User) -> dict[str, Any]:
        user = await self.ensure_user_wallet(user)
        return await self.circle.get_deposit_instructions(str(user.circle_wallet_id))

    async def initiate_withdrawal(
        self,
        user: User,
        *,
        to_address: str,
        amount: Decimal,
        blockchain: str | None = None,
    ) -> WalletTransaction:
        if amount <= 0:
            raise WalletServiceError("Withdrawal amount must be greater than zero.")

        user = await self.ensure_user_wallet(user)
        balance = await self.get_live_balance(user)
        if amount > balance:
            raise InsufficientBalanceError("Insufficient USDC balance for withdrawal.")

        local_tx = WalletTransaction(
            user_id=user.id,
            transaction_type=TransactionType.WITHDRAWAL,
            amount=amount,
            currency="USDC",
            status=TransactionStatus.INITIATED,
            from_address=user.wallet_address,
            to_address=to_address,
            description="USDC withdrawal",
            tx_metadata={"blockchain": blockchain or settings.BLOCKCHAIN},
        )
        self.db.add(local_tx)
        await self.db.flush()

        circle_tx = await self.circle.create_withdrawal(
            from_wallet_id=str(user.circle_wallet_id),
            to_address=to_address,
            amount=amount,
            blockchain=blockchain,
            idempotency_key=str(local_tx.id),
        )
        local_tx.circle_transfer_id = str(circle_tx.get("id") or "")
        local_tx.status = self._status_from_circle_state(str(circle_tx.get("state") or "PENDING"))
        local_tx.onchain_tx_hash = self._extract_tx_hash(circle_tx)
        local_tx.tx_metadata = {**local_tx.tx_metadata, "circleTransaction": circle_tx}

        await self.db.commit()
        await self.db.refresh(local_tx)
        return local_tx

    async def list_transactions(
        self,
        user: User,
        *,
        page: int = 1,
        page_size: int = 20,
        transaction_type: TransactionType | None = None,
    ) -> TransactionListResult:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        stmt = select(WalletTransaction).where(WalletTransaction.user_id == user.id)
        if transaction_type is not None:
            stmt = stmt.where(WalletTransaction.transaction_type == transaction_type)

        total = await self._count(stmt)
        result = await self.db.execute(
            stmt.order_by(WalletTransaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return TransactionListResult(
            transactions=list(result.scalars().all()),
            meta=PaginationMeta(
                total=total,
                page=page,
                page_size=page_size,
                has_next=page * page_size < total,
            ),
        )

    async def get_transaction(self, user: User, tx_id: uuid.UUID) -> WalletTransaction:
        tx = await self.db.get(WalletTransaction, tx_id)
        if tx is None or tx.user_id != user.id:
            raise WalletTransactionNotFoundError("Wallet transaction not found.")
        return tx

    async def get_earnings(
        self, user: User, *, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        result = await self.list_transactions(
            user,
            page=page,
            page_size=page_size,
            transaction_type=TransactionType.EARNING,
        )
        total_earned = await self.db.scalar(
            select(func.coalesce(func.sum(WalletTransaction.amount), 0)).where(
                WalletTransaction.user_id == user.id,
                WalletTransaction.transaction_type == TransactionType.EARNING,
                WalletTransaction.status == TransactionStatus.CONFIRMED,
            )
        )
        return {
            "totalEarned": Decimal(str(total_earned or 0)),
            "transactions": result.transactions,
            "meta": result.meta,
        }

    async def get_active_escrow(self, user: User) -> list[dict[str, Any]]:
        active_statuses = [
            InvoiceStatus.PAYMENT_CHECKING,
            InvoiceStatus.PENDING_RELEASE,
            InvoiceStatus.DISBURSING,
        ]
        result = await self.db.execute(
            select(Invoice)
            .join(Job, Job.id == Invoice.job_id)
            .where(
                Invoice.status.in_(active_statuses),
                or_(Invoice.payer_user_id == user.id, Job.buyer_id == user.id),
            )
            .options(selectinload(Invoice.job).selectinload(Job.agent))
            .order_by(Invoice.created_at.desc())
        )
        invoices = list(result.scalars().unique().all())
        return [
            {
                "invoiceId": invoice.id,
                "jobId": invoice.job_id,
                "agentId": invoice.service_agent_id,
                "agentName": invoice.job.agent.name if invoice.job and invoice.job.agent else None,
                "lockedAmount": invoice.amount,
                "currency": invoice.currency,
                "status": invoice.status.value,
                "createdAt": invoice.created_at,
            }
            for invoice in invoices
        ]

    async def handle_circle_webhook(self, payload: dict[str, Any]) -> WalletTransaction | None:
        transaction = self._extract_circle_transaction(payload)
        if not transaction:
            return None

        circle_id = str(transaction.get("id") or transaction.get("transactionId") or "")
        tx_hash = self._extract_tx_hash(transaction)
        source_address = str(transaction.get("sourceAddress") or "")
        destination_address = str(transaction.get("destinationAddress") or "")
        state = str(transaction.get("state") or transaction.get("status") or "PENDING")
        amount = self._extract_amount(transaction)

        local_tx = await self._find_transaction_for_webhook(
            circle_id=circle_id,
            tx_hash=tx_hash or "",
            source_address=source_address,
            destination_address=destination_address,
            amount=amount,
        )
        if local_tx is None:
            return None

        local_tx.circle_transfer_id = circle_id or local_tx.circle_transfer_id
        local_tx.onchain_tx_hash = tx_hash or local_tx.onchain_tx_hash
        local_tx.from_address = source_address or local_tx.from_address
        local_tx.to_address = destination_address or local_tx.to_address
        local_tx.status = self._status_from_circle_state(state)
        local_tx.tx_metadata = {**local_tx.tx_metadata, "circleWebhook": payload}
        await self.db.commit()
        await self.db.refresh(local_tx)

        if local_tx.status == TransactionStatus.CONFIRMED:
            user = await self.db.get(User, local_tx.user_id)
            if user and user.circle_wallet_id:
                balance = await self.get_live_balance(user)
                await self._trigger_low_balance_notification(user, balance)
        return local_tx

    def verify_circle_signature(self, body: bytes, signature: str | None) -> None:
        if not signature or not settings.CIRCLE_WEBHOOK_SECRET:
            raise CircleWebhookSignatureError("Missing Circle webhook signature configuration.")

        digest = hmac.new(settings.CIRCLE_WEBHOOK_SECRET.encode(), body, hashlib.sha256).digest()
        candidates = {
            digest.hex(),
            base64.b64encode(digest).decode(),
        }
        incoming = signature.strip()
        if "=" in incoming and "," in incoming:
            incoming = incoming.split(",", 1)[0].split("=", 1)[1].strip()

        if not any(hmac.compare_digest(incoming, candidate) for candidate in candidates):
            raise CircleWebhookSignatureError("Invalid Circle webhook signature.")

    async def _trigger_low_balance_notification(self, user: User, balance: Decimal) -> None:
        threshold_raw = user.notification_preferences.get("low_balance_threshold")
        if threshold_raw is None:
            return
        threshold = Decimal(str(threshold_raw))
        if balance >= threshold:
            return

        today = datetime.now(UTC).date().isoformat()
        exists = await self.db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user.id,
                Notification.notification_type == NotificationType.LOW_BALANCE,
                Notification.data["date"].astext == today,
            )
        )
        if exists:
            return

        self.db.add(
            Notification(
                user_id=user.id,
                notification_type=NotificationType.LOW_BALANCE,
                title="Low USDC balance",
                body=f"Your wallet balance is {balance:.6f} USDC, below your threshold.",
                data={"balance": str(balance), "threshold": str(threshold), "date": today},
            )
        )
        await self.db.commit()

    async def _find_transaction_for_webhook(
        self,
        *,
        circle_id: str,
        tx_hash: str,
        source_address: str,
        destination_address: str,
        amount: Decimal,
    ) -> WalletTransaction | None:
        if circle_id:
            result = await self.db.execute(
                select(WalletTransaction).where(WalletTransaction.circle_transfer_id == circle_id)
            )
            tx = result.scalar_one_or_none()
            if tx is not None:
                return tx

        if tx_hash:
            result = await self.db.execute(
                select(WalletTransaction).where(WalletTransaction.onchain_tx_hash == tx_hash)
            )
            tx = result.scalar_one_or_none()
            if tx is not None:
                return tx

        if destination_address and amount > 0:
            user = await self.db.scalar(
                select(User).where(User.wallet_address == destination_address)
            )
            if user is not None:
                local_tx = WalletTransaction(
                    user_id=user.id,
                    transaction_type=TransactionType.DEPOSIT,
                    amount=amount,
                    currency="USDC",
                    status=TransactionStatus.PENDING,
                    circle_transfer_id=circle_id or None,
                    onchain_tx_hash=tx_hash or None,
                    from_address=source_address or None,
                    to_address=destination_address,
                    description="USDC deposit",
                )
                self.db.add(local_tx)
                await self.db.flush()
                return local_tx
        return None

    async def _count(self, stmt: Select[tuple[WalletTransaction]]) -> int:
        subquery = stmt.with_only_columns(WalletTransaction.id).order_by(None).subquery()
        total = await self.db.scalar(select(func.count()).select_from(subquery))
        return int(total or 0)

    def _extract_circle_transaction(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("transaction", "transfer"):
                value = data.get(key)
                if isinstance(value, dict):
                    return value
            if "id" in data or "transactionId" in data:
                return data
        for key in ("transaction", "transfer"):
            value = payload.get(key)
            if isinstance(value, dict):
                return value
        return None

    def _extract_amount(self, transaction: dict[str, Any]) -> Decimal:
        for key in ("amount", "amounts"):
            value = transaction.get(key)
            if isinstance(value, list) and value:
                return Decimal(str(value[0]))
            if value is not None:
                return Decimal(str(value))
        return Decimal("0")

    def _extract_tx_hash(self, transaction: dict[str, Any]) -> str | None:
        for key in ("txHash", "transactionHash", "onchainTxHash"):
            value = transaction.get(key)
            if value:
                return str(value)
        return None

    def _status_from_circle_state(self, state: str) -> TransactionStatus:
        normalized = state.upper()
        if normalized in {"COMPLETE", "CONFIRMED", "SUCCESS", "SUCCEEDED"}:
            return TransactionStatus.CONFIRMED
        if normalized in {"FAILED", "DENIED"}:
            return TransactionStatus.FAILED
        if normalized in {"REFUNDED"}:
            return TransactionStatus.REFUNDED
        return TransactionStatus.PENDING
