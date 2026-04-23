from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.agents import Agent
    from app.models.jobs import Job
    from app.models.users import User


class ReviewStatus(enum.StrEnum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    REMOVED = "REMOVED"


class Review(BaseModel):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_review_job"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # 1–5 star rating enforced by ck_review_rating
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)

    verified_purchase: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    helpful_votes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[ReviewStatus] = mapped_column(
        SAEnum(ReviewStatus, name="review_status", create_type=True),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Relationships
    job: Mapped[Job] = relationship("Job", foreign_keys=[job_id])
    reviewer: Mapped[User] = relationship("User", foreign_keys=[reviewer_id])
    agent: Mapped[Agent] = relationship("Agent", foreign_keys=[agent_id])

    def __repr__(self) -> str:
        return (
            f"<Review id={self.id} rating={self.rating} status={self.status} job_id={self.job_id}>"
        )


__all__ = ["Review", "ReviewStatus"]
