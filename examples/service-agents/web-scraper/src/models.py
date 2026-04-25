from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ServiceConnectRequest(BaseModel):
    session_id: str
    token: str
    orchestrator_ws_url: str
    orchestrator_key: str


class ScrapeArguments(BaseModel):
    url: str
    include_links: bool = False
    max_chars: int | None = None


class StructuredDataArguments(BaseModel):
    url: str
    include_links: bool = True
    include_tables: bool = True
    include_json_ld: bool = True


class CommandMessage(BaseModel):
    command: str
    arguments: dict[str, Any] = {}
