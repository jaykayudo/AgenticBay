from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select

from app.models.spending import AgentSpending
from app.repositories.base import BaseRepository


class AgentSpendingRepository(BaseRepository[AgentSpending]):
    model = AgentSpending

    async def get_total_spent_in_job(
        self,
        job_id: uuid.UUID,
        *,
        master_agent_id: uuid.UUID | None = None,
    ) -> Decimal:
        q = select(func.sum(AgentSpending.amount)).where(AgentSpending.job_id == job_id)
        if master_agent_id is not None:
            q = q.where(AgentSpending.master_agent_id == master_agent_id)
        result = await self.session.execute(q)
        total = result.scalar_one_or_none()
        return total if total is not None else Decimal("0")

    async def log_spend(
        self,
        job_id: uuid.UUID,
        master_agent_id: uuid.UUID,
        sub_agent_id: uuid.UUID,
        invoice_id: uuid.UUID,
        amount: Decimal,
        description: str | None = None,
    ) -> AgentSpending:
        return await self.create(
            job_id=job_id,
            master_agent_id=master_agent_id,
            sub_agent_id=sub_agent_id,
            invoice_id=invoice_id,
            amount=amount,
            description=description,
        )
