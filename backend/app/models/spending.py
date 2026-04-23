from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.agents import Agent
    from app.models.invoices import Invoice
    from app.models.jobs import Job


class AgentSpending(BaseModel):
    """Per-job record of every sub-agent payment made by the master service agent."""

    __tablename__ = "agent_spending"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The service agent that initiated and paid the sub-agent
    master_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # The sub-agent that received the payment
    sub_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # The invoice created for this sub-agent payment
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    job: Mapped[Job] = relationship("Job", foreign_keys=[job_id])
    master_agent: Mapped[Agent] = relationship("Agent", foreign_keys=[master_agent_id])
    sub_agent: Mapped[Agent] = relationship("Agent", foreign_keys=[sub_agent_id])
    invoice: Mapped[Invoice] = relationship("Invoice", foreign_keys=[invoice_id])

    def __repr__(self) -> str:
        return (
            f"<AgentSpending id={self.id} job_id={self.job_id}"
            f" master={self.master_agent_id} sub={self.sub_agent_id} amount={self.amount}>"
        )


__all__ = ["AgentSpending"]
