from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.wallets import EscrowWallet, EscrowWalletStatus
from app.services.circle_client import CircleClient

logger = logging.getLogger(__name__)

# Dust threshold: balances below this are considered empty
_DUST_THRESHOLD = 0.01


class EscrowWalletService:
    def __init__(self, circle: CircleClient) -> None:
        self.circle = circle

    # ─────────────────────────────────────────────────
    # Pool acquisition
    # ─────────────────────────────────────────────────

    async def acquire_wallet(self, invoice_id: str) -> EscrowWallet:
        """
        Claim an AVAILABLE wallet (or create a new one) and lock it to invoice_id.
        Uses SELECT FOR UPDATE SKIP LOCKED so concurrent callers get distinct wallets.
        """
        inv_uuid = uuid.UUID(invoice_id)

        while True:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    stmt = (
                        select(EscrowWallet)
                        .where(EscrowWallet.status == EscrowWalletStatus.AVAILABLE)
                        .limit(1)
                        .with_for_update(skip_locked=True)
                    )
                    result = await session.execute(stmt)
                    wallet = result.scalar_one_or_none()

                    if wallet is None:
                        # Pool exhausted — provision a new Circle wallet
                        wallet = await self._provision_new_wallet(session)
                    else:
                        # Safety: confirm the wallet is truly empty before handing it out
                        balance = await self.circle.get_wallet_balance(wallet.circle_wallet_id)
                        if balance > _DUST_THRESHOLD:
                            logger.warning(
                                "Wallet %s flagged MAINTENANCE — unexpected balance %.6f",
                                wallet.id,
                                balance,
                            )
                            wallet.status = EscrowWalletStatus.MAINTENANCE
                            await session.flush()
                            # Loop again to find/create another
                            continue

                    wallet.status = EscrowWalletStatus.LOCKED
                    wallet.locked_invoice_id = inv_uuid
                    wallet.times_used = (wallet.times_used or 0) + 1
                    await session.flush()
                    return wallet

    async def _provision_new_wallet(self, session: object) -> EscrowWallet:
        """Create a fresh Circle wallet and insert it into the DB (locked)."""
        from sqlalchemy.ext.asyncio import AsyncSession

        circle_wallet = await self.circle.create_developer_wallet(
            wallet_set_id=settings.CIRCLE_WALLET_SET_ID,
            blockchain=settings.BLOCKCHAIN,
        )
        wallet = EscrowWallet(
            circle_wallet_id=circle_wallet["id"],
            circle_wallet_set_id=settings.CIRCLE_WALLET_SET_ID,
            wallet_address=circle_wallet["address"],
            blockchain=settings.BLOCKCHAIN,
            status=EscrowWalletStatus.AVAILABLE,  # acquire_wallet will lock it after
        )
        assert isinstance(session, AsyncSession)
        session.add(wallet)
        await session.flush()
        return wallet

    # ─────────────────────────────────────────────────
    # Pool release
    # ─────────────────────────────────────────────────

    async def release_wallet(self, wallet_id: str) -> bool:
        """
        Return a wallet to AVAILABLE after disbursement completes.
        Verifies the balance is zero (or dust) first.
        """
        wid = uuid.UUID(wallet_id)
        async with AsyncSessionLocal() as session:
            wallet = await session.get(EscrowWallet, wid)
            if wallet is None:
                return False

            balance = await self.circle.get_wallet_balance(wallet.circle_wallet_id)
            if balance > _DUST_THRESHOLD:
                logger.warning(
                    "Wallet %s cannot be released — balance %.6f > dust threshold",
                    wallet_id,
                    balance,
                )
                wallet.status = EscrowWalletStatus.MAINTENANCE
            else:
                wallet.status = EscrowWalletStatus.AVAILABLE
                wallet.locked_invoice_id = None
                wallet.current_balance = Decimal("0")

            wallet.last_balance_check_at = datetime.now(UTC)
            await session.commit()
            return wallet.status == EscrowWalletStatus.AVAILABLE

    # ─────────────────────────────────────────────────
    # Payment verification
    # ─────────────────────────────────────────────────

    async def verify_payment_received(
        self, circle_wallet_id: str, expected_amount: float
    ) -> dict[str, object] | None:
        """
        Confirm the escrow wallet has received at least expected_amount USDC.
        Returns transaction details if confirmed, else None.
        """
        balance = await self.circle.get_wallet_balance(circle_wallet_id)
        if balance < expected_amount:
            return None

        # Find the inbound transaction that brought the funds in
        txns = await self.circle.get_wallet_transactions(circle_wallet_id, page_size=10)
        for txn in txns:
            if txn.get("transactionType") not in ("INBOUND", "TRANSFER"):
                continue
            txn_amounts: list[dict[str, object]] = txn.get("amounts", [])
            for amt_entry in txn_amounts:
                if float(str(amt_entry.get("amount", "0"))) >= expected_amount:
                    tx_hash: str = str(txn.get("txHash", ""))
                    blockchain: str = str(txn.get("blockchain", settings.BLOCKCHAIN))
                    return {
                        "transaction_id": str(txn.get("id", "")),
                        "tx_hash": tx_hash,
                        "tx_url": CircleClient.get_explorer_url(tx_hash, blockchain),
                        "amount": float(str(amt_entry.get("amount", "0"))),
                        "from_address": str(txn.get("sourceAddress", "")),
                        "confirmed_at": str(txn.get("updateDate", "")),
                    }

        # Balance confirmed but no matching transaction found yet (rare race)
        return None

    # ─────────────────────────────────────────────────
    # Balance sync (for background task)
    # ─────────────────────────────────────────────────

    async def sync_all_balances(self) -> None:
        """Refresh current_balance on every wallet in the pool."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(EscrowWallet))
            wallets = list(result.scalars().all())

        for wallet in wallets:
            try:
                balance = await self.circle.get_wallet_balance(wallet.circle_wallet_id)
                async with AsyncSessionLocal() as session:
                    w = await session.get(EscrowWallet, wallet.id)
                    if w:
                        w.current_balance = Decimal(str(balance))
                        w.last_balance_check_at = datetime.now(UTC)
                        await session.commit()
            except Exception:
                logger.exception("Balance sync failed for wallet %s", wallet.id)
