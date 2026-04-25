from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ServiceConnectRequest(BaseModel):
    session_id: str
    token: str
    orchestrator_ws_url: str
    orchestrator_key: str


class ResearchArguments(BaseModel):
    topic: str
    sources: list[str] = []
    depth: str = "standard"
    max_sources: int = 5


class CommandMessage(BaseModel):
    command: str
    arguments: dict[str, Any] = {}
