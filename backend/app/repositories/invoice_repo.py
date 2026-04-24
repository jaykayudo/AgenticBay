from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.invoices import Invoice, InvoiceStatus
from app.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    model = Invoice

    async def get_by_session(self, session_id: uuid.UUID) -> list[Invoice]:
        result = await self.session.execute(select(Invoice).where(Invoice.session_id == session_id))
        return list(result.scalars().all())

    async def get_pending_release_by_session(self, session_id: uuid.UUID) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice)
            .where(
                Invoice.session_id == session_id,
                Invoice.status == InvoiceStatus.PENDING_RELEASE,
            )
            .options(selectinload(Invoice.escrow_wallet))
        )
        return list(result.scalars().all())

    async def get_by_escrow_wallet(
        self, wallet_id: uuid.UUID, *, status: InvoiceStatus | None = None
    ) -> Invoice | None:
        stmt = select(Invoice).where(Invoice.escrow_wallet_id == wallet_id)
        if status is not None:
            stmt = stmt.where(Invoice.status == status)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_expired_unpaid(self, now: datetime) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice).where(
                Invoice.status == InvoiceStatus.PENDING,
                Invoice.expires_at <= now,
            )
        )
        return list(result.scalars().all())

    async def mark_payment_checking(self, invoice_id: uuid.UUID) -> Invoice | None:
        return await self.update(invoice_id, status=InvoiceStatus.PAYMENT_CHECKING)

    async def mark_pending_release(
        self,
        invoice_id: uuid.UUID,
        *,
        payment_transaction_id: str,
        payment_tx_hash: str | None = None,
        payment_tx_url: str | None = None,
        payer_wallet_address: str | None = None,
    ) -> Invoice | None:
        kwargs: dict[str, Any] = {
            "status": InvoiceStatus.PENDING_RELEASE,
            "paid_at": datetime.now(UTC),
            "payment_transaction_id": payment_transaction_id,
        }
        if payment_tx_hash is not None:
            kwargs["payment_tx_hash"] = payment_tx_hash
        if payment_tx_url is not None:
            kwargs["payment_tx_url"] = payment_tx_url
        if payer_wallet_address is not None:
            kwargs["payer_wallet_address"] = payer_wallet_address
        return await self.update(invoice_id, **kwargs)

    async def mark_disbursing(self, invoice_id: uuid.UUID) -> Invoice | None:
        return await self.update(invoice_id, status=InvoiceStatus.DISBURSING)

    async def mark_disbursed(
        self,
        invoice_id: uuid.UUID,
        *,
        agent_disbursement_tx_id: str | None = None,
        agent_disbursement_tx_hash: str | None = None,
        fee_disbursement_tx_id: str | None = None,
        fee_disbursement_tx_hash: str | None = None,
    ) -> Invoice | None:
        kwargs: dict[str, Any] = {
            "status": InvoiceStatus.DISBURSED,
            "disbursed_at": datetime.now(UTC),
        }
        if agent_disbursement_tx_id is not None:
            kwargs["agent_disbursement_tx_id"] = agent_disbursement_tx_id
        if agent_disbursement_tx_hash is not None:
            kwargs["agent_disbursement_tx_hash"] = agent_disbursement_tx_hash
        if fee_disbursement_tx_id is not None:
            kwargs["fee_disbursement_tx_id"] = fee_disbursement_tx_id
        if fee_disbursement_tx_hash is not None:
            kwargs["fee_disbursement_tx_hash"] = fee_disbursement_tx_hash
        return await self.update(invoice_id, **kwargs)

    async def mark_refunded(
        self,
        invoice_id: uuid.UUID,
        *,
        refund_tx_id: str | None = None,
        refund_tx_hash: str | None = None,
    ) -> Invoice | None:
        kwargs: dict[str, Any] = {
            "status": InvoiceStatus.REFUNDED,
            "refunded_at": datetime.now(UTC),
        }
        if refund_tx_id is not None:
            kwargs["refund_tx_id"] = refund_tx_id
        if refund_tx_hash is not None:
            kwargs["refund_tx_hash"] = refund_tx_hash
        return await self.update(invoice_id, **kwargs)

    async def mark_failed(self, invoice_id: uuid.UUID) -> Invoice | None:
        return await self.update(invoice_id, status=InvoiceStatus.FAILED)

    async def mark_expired(self, invoice_id: uuid.UUID) -> Invoice | None:
        return await self.update(invoice_id, status=InvoiceStatus.EXPIRED)
