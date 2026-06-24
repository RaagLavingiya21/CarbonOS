"""Shared LangGraph checkpointer for Phase 2 (MemorySaver until Supabase in Phase 3)."""

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

_checkpointer = MemorySaver()


def get_checkpointer() -> MemorySaver:
    return _checkpointer
