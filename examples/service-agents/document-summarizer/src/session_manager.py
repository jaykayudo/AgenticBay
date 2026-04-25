from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    session_id: str
    orchestrator_ws: Any = None  # OrchestratorWSClient, avoid circular import
    paid: bool = False
    paid_invoice_ids: list[str] = field(default_factory=list)
    pending_document: str | None = None


class SessionManager:
    """In-memory session store. For production use Redis."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def create(self, session_id: str) -> SessionState:
        state = SessionState(session_id=session_id)
        self._sessions[session_id] = state
        return state

    def get(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def mark_paid(self, session_id: str, invoice_id: str) -> None:
        state = self.get(session_id)
        if state:
            state.paid = True
            state.paid_invoice_ids.append(invoice_id)

    @property
    def active_count(self) -> int:
        return len(self._sessions)
