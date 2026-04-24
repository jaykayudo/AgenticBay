from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.models.wallets import EscrowWallet, EscrowWalletStatus
from app.repositories.base import BaseRepository


class EscrowWalletRepository(BaseRepository[EscrowWallet]):
    model = EscrowWallet

    async def get_by_circle_id(self, circle_wallet_id: str) -> EscrowWallet | None:
        result = await self.session.execute(
            select(EscrowWallet).where(EscrowWallet.circle_wallet_id == circle_wallet_id)
        )
        return result.scalar_one_or_none()

    async def get_by_address(self, wallet_address: str) -> EscrowWallet | None:
        result = await self.session.execute(
            select(EscrowWallet).where(EscrowWallet.wallet_address == wallet_address)
        )
        return result.scalar_one_or_none()

    async def get_all_locked(self) -> list[EscrowWallet]:
        result = await self.session.execute(
            select(EscrowWallet).where(EscrowWallet.status == EscrowWalletStatus.LOCKED)
        )
        return list(result.scalars().all())

    async def release_wallet(self, wallet_id: uuid.UUID) -> EscrowWallet | None:
        return await self.update(
            wallet_id,
            status=EscrowWalletStatus.AVAILABLE,
            locked_invoice_id=None,
            current_balance=Decimal("0"),
            last_balance_check_at=datetime.now(UTC),
        )

    async def update_balance(self, wallet_id: uuid.UUID, balance: Decimal) -> EscrowWallet | None:
        return await self.update(
            wallet_id,
            current_balance=balance,
            last_balance_check_at=datetime.now(UTC),
        )
