from __future__ import annotations

import asyncio
import logging

from app.services.circle_client import CircleClient
from app.services.escrow_wallet_service import EscrowWalletService
from app.services.invoice_service import InvoiceService

logger = logging.getLogger(__name__)

_invoice_svc = InvoiceService()
_escrow_svc = EscrowWalletService(CircleClient())


async def expire_unpaid_invoices_task() -> None:
    """Run every 5 minutes — mark unpaid invoices past expiry as EXPIRED."""
    while True:
        try:
            count = await _invoice_svc.expire_unpaid_invoices()
            if count:
                logger.info("Expired %d unpaid invoice(s)", count)
        except Exception:
            logger.exception("expire_unpaid_invoices_task error")
        await asyncio.sleep(300)  # 5 minutes


async def sync_wallet_balances_task() -> None:
    """Run every 10 minutes — refresh current_balance on all escrow wallets."""
    while True:
        try:
            await _escrow_svc.sync_all_balances()
        except Exception:
            logger.exception("sync_wallet_balances_task error")
        await asyncio.sleep(600)  # 10 minutes


async def reconcile_locked_wallets_task() -> None:
    """
    Run every 30 minutes — verify that LOCKED wallets still have an active
    PENDING/PENDING_RELEASE invoice.  Orphaned locks are released.
    """
    while True:
        await asyncio.sleep(1800)  # 30 minutes
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.invoices import InvoiceStatus
            from app.repositories.wallet_repo import EscrowWalletRepository

            async with AsyncSessionLocal() as session:
                repo = EscrowWalletRepository(session)
                locked = await repo.get_all_locked()

            for wallet in locked:
                if not wallet.locked_invoice_id:
                    await _escrow_svc.release_wallet(str(wallet.id))
                    continue
                async with AsyncSessionLocal() as session:
                    from app.repositories.invoice_repo import InvoiceRepository

                    invoice = await InvoiceRepository(session).get_by_id(wallet.locked_invoice_id)
                if invoice and invoice.status in (
                    InvoiceStatus.PENDING,
                    InvoiceStatus.PAYMENT_CHECKING,
                    InvoiceStatus.PENDING_RELEASE,
                    InvoiceStatus.DISBURSING,
                ):
                    continue  # legitimately locked
                logger.warning(
                    "Releasing orphaned wallet %s (invoice %s status=%s)",
                    wallet.id,
                    wallet.locked_invoice_id,
                    invoice.status if invoice else "missing",
                )
                await _escrow_svc.release_wallet(str(wallet.id))

        except Exception:
            logger.exception("reconcile_locked_wallets_task error")
