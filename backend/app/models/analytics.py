from __future__ import annotations

import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.agents import Agent


class AnalyticPeriod(enum.StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class AgentAnalytic(BaseModel):
    __tablename__ = "agent_analytics"
    __table_args__ = (
        UniqueConstraint(
            "agent_id", "period", "period_start",
            name="uq_agent_analytic_period",
        ),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    period: Mapped[AnalyticPeriod] = mapped_column(
        SAEnum(AnalyticPeriod, name="analytic_period", create_type=True),
        nullable=False,
        index=True,
    )

    # Inclusive start date of the rollup window
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Job counts
    total_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Revenue
    total_revenue: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=6), default=Decimal("0"), nullable=False
    )

    # Quality
    avg_rating: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=3, scale=2), nullable=True
    )
    avg_duration_sec: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=2), nullable=True
    )

    # Per-action invocation counts: {"action_name": count, ...}
    action_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )

    # Relationships
    agent: Mapped[Agent] = relationship("Agent", foreign_keys=[agent_id])

    def __repr__(self) -> str:
        return (
            f"<AgentAnalytic id={self.id} agent_id={self.agent_id}"
            f" period={self.period} period_start={self.period_start}>"
        )


__all__ = ["AgentAnalytic", "AnalyticPeriod"]
