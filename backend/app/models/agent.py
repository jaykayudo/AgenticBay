from typing import Any

from sqlalchemy import JSON, Boolean, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class RegisteredAgent(BaseModel):
    __tablename__ = "registered_agents"

    external_agent_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
