from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.invoices import Invoice, InvoiceStatus
from app.models.wallets import EscrowWallet
from app.repositories.invoice_repo import InvoiceRepository
from app.services.circle_client import CircleClient
from app.services.escrow_wallet_service import EscrowWalletService

logger = logging.getLogger(__name__)

INVOICE_EXPIRY_MINUTES = 30


class InvoiceService:
    def __init__(self) -> None:
        self.circle = CircleClient()
        self.escrow = EscrowWalletService(self.circle)

    # ─────────────────────────────────────────────────
    # Creation
    # ─────────────────────────────────────────────────

    async def create_invoice(
        self,
        *,
        session_id: str,
        job_id: str,
        payer_user_id: str,
        service_agent_id: str,
        amount: float,
        description: str,
        payee_wallet_address: str | None = None,
    ) -> tuple[Invoice, EscrowWallet]:
        """
        Create a DB invoice and assign an escrow wallet.
        Returns (invoice, escrow_wallet) with all fields populated.
        """
        fee_pct = Decimal(str(settings.MARKETPLACE_FEE_PERCENT)) / Decimal("100")
        amount_dec = Decimal(str(amount))
        marketplace_fee = (amount_dec * fee_pct).quantize(Decimal("0.000001"))
        agent_payout = amount_dec - marketplace_fee

        # Resolve payee address from service agent record if not provided
        if not payee_wallet_address:
            payee_wallet_address = await self._get_agent_wallet(service_agent_id)

        async with AsyncSessionLocal() as session:
            invoice_repo = InvoiceRepository(session)
            invoice = await invoice_repo.create(
                session_id=uuid.UUID(session_id),
                job_id=uuid.UUID(job_id),
                payer_user_id=uuid.UUID(payer_user_id),
                service_agent_id=uuid.UUID(service_agent_id),
                amount=amount_dec,
                marketplace_fee=marketplace_fee,
                agent_payout=agent_payout,
                description=description,
                payee_wallet_address=payee_wallet_address,
                marketplace_wallet_address=settings.MARKETPLACE_WALLET_ADDRESS,
                status=InvoiceStatus.PENDING,
                expires_at=datetime.now(UTC) + timedelta(minutes=INVOICE_EXPIRY_MINUTES),
            )
            await session.commit()

        # Acquire escrow wallet outside the invoice-creation transaction
        # so a Circle API failure doesn't roll back the invoice record
        escrow_wallet = await self.escrow.acquire_wallet(str(invoice.id))

        # Link wallet to invoice
        async with AsyncSessionLocal() as session:
            inv = await session.get(Invoice, invoice.id)
            if inv:
                inv.escrow_wallet_id = escrow_wallet.id
                await session.commit()
                invoice = inv

        return invoice, escrow_wallet

    # ─────────────────────────────────────────────────
    # Payment confirmation
    # ─────────────────────────────────────────────────

    async def confirm_payment(self, invoice_id: str) -> bool:
        """
        Verify the escrow wallet has received the expected amount.
        Updates invoice to PENDING_RELEASE on success.
        """
        inv_uuid = uuid.UUID(invoice_id)
        async with AsyncSessionLocal() as session:
            invoice = await session.get(
                Invoice, inv_uuid, options=[selectinload(Invoice.escrow_wallet)]
            )
            if not invoice or invoice.status not in (
                InvoiceStatus.PENDING,
                InvoiceStatus.PAYMENT_CHECKING,
            ):
                return False

            wallet = invoice.escrow_wallet
            if not wallet:
                logger.error("Invoice %s has no escrow wallet", invoice_id)
                return False

            invoice.status = InvoiceStatus.PAYMENT_CHECKING
            await session.commit()

        tx_details = await self.escrow.verify_payment_received(
            wallet.circle_wallet_id, float(invoice.amount)
        )
        if not tx_details:
            return False

        async with AsyncSessionLocal() as session:
            repo = InvoiceRepository(session)
            await repo.mark_pending_release(
                inv_uuid,
                payment_transaction_id=str(tx_details["transaction_id"]),
                payment_tx_hash=str(tx_details.get("tx_hash", "")),
                payment_tx_url=str(tx_details.get("tx_url", "")),
                payer_wallet_address=str(tx_details.get("from_address", "")),
            )
            await session.commit()

        return True

    # ─────────────────────────────────────────────────
    # Webhook handler (Circle → platform)
    # ─────────────────────────────────────────────────

    async def handle_payment_webhook(self, webhook_data: dict[str, Any]) -> bool:
        """
        Process a Circle `transactions.inbound` webhook.
        Idempotent — ignores already-processed invoices.
        """
        notification: dict[str, Any] = webhook_data.get("notification", {})
        transaction: dict[str, Any] = notification.get("transaction", {})
        wallet_id_str: str = str(transaction.get("walletId", ""))
        tx_id: str = str(transaction.get("id", ""))

        if not wallet_id_str or not tx_id:
            return False

        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            from app.models.wallets import EscrowWallet

            result = await session.execute(
                select(EscrowWallet).where(EscrowWallet.circle_wallet_id == wallet_id_str)
            )
            wallet = result.scalar_one_or_none()
            if not wallet or not wallet.locked_invoice_id:
                return False

            from app.repositories.invoice_repo import InvoiceRepository

            repo = InvoiceRepository(session)
            invoice = await repo.get_by_id(wallet.locked_invoice_id)
            if not invoice or invoice.status != InvoiceStatus.PENDING:
                return False  # already processed or wrong state

            # Extract amount from webhook
            amounts: list[dict[str, Any]] = transaction.get("amounts", [])
            tx_amount = sum(float(str(a.get("amount", "0"))) for a in amounts)
            if tx_amount < float(invoice.amount):
                logger.warning(
                    "Webhook amount %.6f < invoice amount %.6f for invoice %s",
                    tx_amount,
                    invoice.amount,
                    invoice.id,
                )
                return False

            tx_hash = str(transaction.get("txHash", ""))
            blockchain = str(transaction.get("blockchain", settings.BLOCKCHAIN))
            await repo.mark_pending_release(
                invoice.id,
                payment_transaction_id=tx_id,
                payment_tx_hash=tx_hash,
                payment_tx_url=CircleClient.get_explorer_url(tx_hash, blockchain),
                payer_wallet_address=str(transaction.get("sourceAddress", "")),
            )
            await session.commit()

        return True

    # ─────────────────────────────────────────────────
    # Disbursement
    # ─────────────────────────────────────────────────

    async def disburse_session_invoices(self, session_id: str) -> list[dict[str, Any]]:
        """
        Transfer funds from each PENDING_RELEASE escrow wallet:
          - agent_payout  → service agent wallet
          - marketplace_fee → marketplace wallet
        Returns a result dict per invoice.
        """
        async with AsyncSessionLocal() as session:
            repo = InvoiceRepository(session)
            invoices = await repo.get_pending_release_by_session(uuid.UUID(session_id))

        results: list[dict[str, Any]] = []
        for invoice in invoices:
            result = await self._disburse_one(invoice)
            results.append(result)
        return results

    async def _disburse_one(self, invoice: Invoice) -> dict[str, Any]:
        invoice_id = invoice.id

        async with AsyncSessionLocal() as session:
            repo = InvoiceRepository(session)
            await repo.mark_disbursing(invoice_id)
            await session.commit()

        wallet = invoice.escrow_wallet
        if not wallet:
            async with AsyncSessionLocal() as session:
                await InvoiceRepository(session).mark_failed(invoice_id)
                await session.commit()
            return {"invoice_id": str(invoice_id), "success": False, "error": "no escrow wallet"}

        try:
            # 1 — Transfer to service agent
            agent_tx = await self.circle.create_transfer(
                from_wallet_id=wallet.circle_wallet_id,
                to_address=str(invoice.payee_wallet_address or ""),
                amount=float(invoice.agent_payout),
                idempotency_key=f"agent-{invoice_id}",
            )
            agent_tx = await self.circle.wait_for_transfer_completion(agent_tx["id"])

            # 2 — Transfer marketplace fee
            fee_tx = await self.circle.create_transfer(
                from_wallet_id=wallet.circle_wallet_id,
                to_address=settings.MARKETPLACE_WALLET_ADDRESS,
                amount=float(invoice.marketplace_fee),
                idempotency_key=f"fee-{invoice_id}",
            )
            fee_tx = await self.circle.wait_for_transfer_completion(fee_tx["id"])

            async with AsyncSessionLocal() as session:
                repo = InvoiceRepository(session)
                await repo.mark_disbursed(
                    invoice_id,
                    agent_disbursement_tx_id=agent_tx.get("id"),
                    agent_disbursement_tx_hash=agent_tx.get("txHash"),
                    fee_disbursement_tx_id=fee_tx.get("id"),
                    fee_disbursement_tx_hash=fee_tx.get("txHash"),
                )
                await session.commit()

            await self.escrow.release_wallet(str(wallet.id))
            return {"invoice_id": str(invoice_id), "success": True}

        except Exception as exc:
            logger.exception("Disbursement failed for invoice %s", invoice_id)
            async with AsyncSessionLocal() as session:
                await InvoiceRepository(session).mark_failed(invoice_id)
                await session.commit()
            return {"invoice_id": str(invoice_id), "success": False, "error": str(exc)}

    # ─────────────────────────────────────────────────
    # Refund
    # ─────────────────────────────────────────────────

    async def refund_invoice(self, invoice_id: str, reason: str) -> bool:
        """Transfer escrow funds back to the payer and mark invoice REFUNDED."""
        inv_uuid = uuid.UUID(invoice_id)
        async with AsyncSessionLocal() as session:
            invoice = await session.get(
                Invoice, inv_uuid, options=[selectinload(Invoice.escrow_wallet)]
            )
            if not invoice or invoice.status != InvoiceStatus.PENDING_RELEASE:
                return False

        wallet = invoice.escrow_wallet
        payer_address = invoice.payer_wallet_address
        if not wallet or not payer_address:
            return False

        try:
            refund_tx = await self.circle.create_transfer(
                from_wallet_id=wallet.circle_wallet_id,
                to_address=payer_address,
                amount=float(invoice.amount),
                idempotency_key=f"refund-{invoice_id}",
            )
            refund_tx = await self.circle.wait_for_transfer_completion(refund_tx["id"])

            async with AsyncSessionLocal() as session:
                await InvoiceRepository(session).mark_refunded(
                    inv_uuid,
                    refund_tx_id=refund_tx.get("id"),
                    refund_tx_hash=refund_tx.get("txHash"),
                )
                await session.commit()

            await self.escrow.release_wallet(str(wallet.id))
            return True

        except Exception:
            logger.exception("Refund failed for invoice %s", invoice_id)
            return False

    # ─────────────────────────────────────────────────
    # Expiry
    # ─────────────────────────────────────────────────

    async def expire_unpaid_invoices(self) -> int:
        """Mark PENDING invoices past their expires_at as EXPIRED. Returns count."""
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as session:
            repo = InvoiceRepository(session)
            expired = await repo.get_expired_unpaid(now)
            for invoice in expired:
                await repo.mark_expired(invoice.id)
                if invoice.escrow_wallet_id:
                    await session.flush()
            await session.commit()

        # Release any escrow wallets that were prematurely acquired
        for invoice in expired:
            if invoice.escrow_wallet_id:
                try:
                    await self.escrow.release_wallet(str(invoice.escrow_wallet_id))
                except Exception:
                    logger.exception("Wallet release failed for expired invoice %s", invoice.id)

        return len(expired)

    # ─────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────

    async def _get_agent_wallet(self, agent_id: str) -> str | None:
        from app.repositories.agent_repo import AgentRepository

        async with AsyncSessionLocal() as session:
            agent = await AgentRepository(session).get_by_id(uuid.UUID(agent_id))
        return agent.wallet_address if agent else None
