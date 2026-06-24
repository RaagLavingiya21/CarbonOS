"""Lightweight in-memory workflow sessions for the Phase 1 API layer.

Supabase-backed persistence is planned for a later phase. For now, this store
replaces Streamlit's session state for API clients while analyses continue to
persist through the existing SQLite modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any
from uuid import uuid4


@dataclass
class WorkflowSession:
    session_id: str
    workflow: str
    phase: str
    data: dict[str, Any] = field(default_factory=dict)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, WorkflowSession] = {}
        self._lock = Lock()

    def create(self, workflow: str, phase: str, **data: Any) -> WorkflowSession:
        session = WorkflowSession(
            session_id=str(uuid4()),
            workflow=workflow,
            phase=phase,
            data=dict(data),
        )
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str, workflow: str | None = None) -> WorkflowSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            return None
        if workflow is not None and session.workflow != workflow:
            return None
        return session

    def update(self, session_id: str, *, phase: str | None = None, **data: Any) -> WorkflowSession:
        with self._lock:
            session = self._sessions[session_id]
            if phase is not None:
                session.phase = phase
            session.data.update(data)
            return session

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None


session_store = SessionStore()
