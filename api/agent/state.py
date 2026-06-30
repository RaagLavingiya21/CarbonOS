"""LangGraph state for the platform chat agent."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """State passed between nodes in the platform chat agent graph."""

    messages: list[dict[str, str]]
    user_id: str
    access_token: str
    thread_id: str | None
    context_layers: dict[str, Any]
    active_skill: str | None
    skill_params: dict[str, Any] | None
    skill_result: dict[str, Any] | None
    assistant_content: str
    suggestions: list[str]
    module_launch: dict[str, Any] | None
