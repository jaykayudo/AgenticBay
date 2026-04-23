from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.models.invoices import Invoice, InvoiceStatus
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    model = Invoice

    async def get_by_onchain_id(self, onchain_invoice_id: str) -> Invoice | None:
        result = await self.session.execute(
            select(Invoice).where(Invoice.onchain_invoice_id == onchain_invoice_id)
        )
        return result.scalar_one_or_none()

    async def get_by_session(self, session_id: uuid.UUID) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice).where(Invoice.session_id == session_id)
        )
        return list(result.scalars().all())

    async def mark_paid(
        self,
        invoice_id: uuid.UUID,
        *,
        payment_tx_hash: str | None = None,
    ) -> Invoice | None:
        kwargs: dict[str, Any] = {
            "status": InvoiceStatus.PAID,
            "paid_at": datetime.now(UTC),
        }
        if payment_tx_hash is not None:
            kwargs["payment_tx_hash"] = payment_tx_hash
        return await self.update(invoice_id, **kwargs)

    async def mark_disbursed(
        self,
        invoice_id: uuid.UUID,
        *,
        disbursement_tx_hash: str | None = None,
    ) -> Invoice | None:
        kwargs: dict[str, Any] = {
            "status": InvoiceStatus.DISBURSED,
            "disbursed_at": datetime.now(UTC),
        }
        if disbursement_tx_hash is not None:
            kwargs["disbursement_tx_hash"] = disbursement_tx_hash
        return await self.update(invoice_id, **kwargs)
