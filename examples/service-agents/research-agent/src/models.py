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
    context: str | None = None
    focus_areas: list[str] | None = None
    constraints: list[str] | None = None


class ResearchBrief(BaseModel):
    topic: str
    executive_summary: str
    key_findings: list[str]
    assumptions_and_caveats: list[str]
    open_questions: list[str]
    recommended_next_steps: list[str]
    focus_areas: list[str] | None = None
    evidence_notes: list[str] | None = None
    extra: dict[str, Any] | None = None
