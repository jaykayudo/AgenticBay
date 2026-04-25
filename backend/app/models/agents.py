from __future__ import annotations

import enum
import secrets
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.users import User


class AgentHostingType(enum.StrEnum):
    EXTERNALLY_HOSTED = "EXTERNALLY_HOSTED"


class AgentStatus(enum.StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    SUSPENDED = "SUSPENDED"
    REJECTED = "REJECTED"


class Agent(BaseModel):
    __tablename__ = "agents"

    # Ownership
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Identity
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Hosting — always EXTERNALLY_HOSTED; kept as enum for future extensibility
    hosting_type: Mapped[AgentHostingType] = mapped_column(
        SAEnum(AgentHostingType, name="agent_hosting_type", create_type=True),
        default=AgentHostingType.EXTERNALLY_HOSTED,
        nullable=False,
    )
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_code_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Lifecycle
    status: Mapped[AgentStatus] = mapped_column(
        SAEnum(AgentStatus, name="agent_status", create_type=True),
        default=AgentStatus.PENDING,
        nullable=False,
        index=True,
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Categorisation
    categories: Mapped[list[Any]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    tags: Mapped[list[Any]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )

    # Payments — Circle wallet created by marketplace on listing submission
    circle_wallet_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    wallet_address: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )

    # Smart contract proxy deployed by factory on activation
    proxy_contract_address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Issued at listing time; sent as X-Orchestrator-Key on every HTTP invocation.
    # Unique per agent so a key from agent A cannot be used against agent B.
    orchestrator_api_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: secrets.token_urlsafe(32),
    )

    # Vector search — reference ID in the agent_embeddings table
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Cached capability document fetched from /capabilities; refreshed on each CONNECT
    capabilities_cache: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Pricing as supplied in the listing form (range or fixed; shape is agent-defined)
    pricing_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )

    # Health tracking — updated by background health check task
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_health_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    consecutive_health_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    agent_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Denormalized stats — updated by background jobs, not on every request
    total_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_rate: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2), default=Decimal("0.00"), nullable=False
    )
    avg_rating: Mapped[Decimal] = mapped_column(
        Numeric(precision=3, scale=2), default=Decimal("0.00"), nullable=False
    )
    total_earned: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=6), default=Decimal("0"), nullable=False
    )
    avg_duration_sec: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=2), nullable=True
    )

    # Relationships
    owner: Mapped[User] = relationship("User", foreign_keys=[owner_id])
    actions: Mapped[list[AgentAction]] = relationship(
        "AgentAction", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Agent id={self.id} name={self.name} status={self.status}>"


class AgentAction(BaseModel):
    """A single callable action exposed by a service agent."""

    __tablename__ = "agent_actions"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Matches the command name used in {"command": "<name>", "arguments": {}}
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # JSON Schema objects describing expected inputs and outputs
    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )
    output_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )

    # Per-action price in USDC; None means free or bundled in agent pricing
    price: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=6), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    agent: Mapped[Agent] = relationship("Agent", back_populates="actions")

    def __repr__(self) -> str:
        return f"<AgentAction id={self.id} name={self.name} agent_id={self.agent_id}>"


__all__ = ["Agent", "AgentAction", "AgentStatus", "AgentHostingType"]
