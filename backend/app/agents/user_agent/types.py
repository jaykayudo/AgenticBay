from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class AgentState(StrEnum):
    IDLE = "IDLE"
    SEARCHING = "SEARCHING"
    CONNECTING = "CONNECTING"
    ACTIVE = "ACTIVE"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    AWAITING_USER = "AWAITING_USER"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


class FrontendMessage(BaseModel):
    """Inbound message from user frontend over the chat WebSocket."""

    type: str
    data: dict[str, Any] = {}


class AutoPaySettings(BaseModel):
    auto_pay_enabled: bool
    auto_pay_max_per_job: float
    auto_pay_max_per_day: float
