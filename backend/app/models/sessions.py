from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.agents import Agent
    from app.models.jobs import Job
    from app.models.users import User


class SessionPhase(enum.StrEnum):
    STARTED = "STARTED"
    SEARCHING = "SEARCHING"
    CONNECTING = "CONNECTING"
    ACTIVE = "ACTIVE"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


class ConnectionType(enum.StrEnum):
    WEBSOCKET = "WEBSOCKET"
    WEBHOOK = "WEBHOOK"


class MessageDirection(enum.StrEnum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class AgentType(enum.StrEnum):
    USER = "USER"
    ORCHESTRATOR = "ORCHESTRATOR"
    SERVICE = "SERVICE"


class Session(BaseModel):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Null until user sends CONNECT_AGENT
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    phase: Mapped[SessionPhase] = mapped_column(
        SAEnum(SessionPhase, name="session_phase", create_type=True),
        default=SessionPhase.STARTED,
        nullable=False,
        index=True,
    )

    # How the user agent is connected to receive orchestrator messages
    connection_type: Mapped[ConnectionType] = mapped_column(
        SAEnum(ConnectionType, name="connection_type", create_type=True),
        default=ConnectionType.WEBSOCKET,
        nullable=False,
    )

    # JWT issued at session start; used to authenticate WebSocket connection
    job_session_auth_token: Mapped[str] = mapped_column(String(512), nullable=False)

    # Webhook URL for WEBHOOK connection type; used as fallback delivery
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # HMAC secret for signing outbound messages to the user agent
    hmac_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Full Redis-recoverable snapshot of JobSessionState (Pydantic model)
    graph_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", foreign_keys=[user_id])
    agent: Mapped[Agent | None] = relationship("Agent", foreign_keys=[agent_id])
    messages: Mapped[list[Message]] = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan"
    )
    jobs: Mapped[list[Job]] = relationship(
        "Job", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} phase={self.phase} user_id={self.user_id}>"


class Message(BaseModel):
    """Full audit log of every message exchanged within a job session."""

    __tablename__ = "messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    direction: Mapped[MessageDirection] = mapped_column(
        SAEnum(MessageDirection, name="message_direction", create_type=True),
        nullable=False,
    )
    from_agent_type: Mapped[AgentType] = mapped_column(
        SAEnum(AgentType, name="agent_type", create_type=True),
        nullable=False,
    )
    to_agent_type: Mapped[AgentType] = mapped_column(
        # Reuse the same DB enum type — SQLAlchemy deduplicates by name
        SAEnum(AgentType, name="agent_type", create_type=False),
        nullable=False,
    )

    # The "type" field of the message envelope (START, SEARCH_AGENT, PAYMENT, etc.)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Full text content of the message (JSON-encapsulated as text per spec)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    session: Mapped[Session] = relationship("Session", back_populates="messages")

    def __repr__(self) -> str:
        return (
            f"<Message id={self.id} type={self.message_type}"
            f" dir={self.direction} session_id={self.session_id}>"
        )


__all__ = [
    "Session",
    "Message",
    "SessionPhase",
    "ConnectionType",
    "MessageDirection",
    "AgentType",
]
