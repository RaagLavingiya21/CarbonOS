"""Shared helpers for invoking and resuming LangGraph workflows."""

from __future__ import annotations

from typing import Any

from langgraph.graph.state import CompiledStateGraph


def thread_config(session_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": session_id}}


def invoke_graph(
    graph: CompiledStateGraph,
    session_id: str,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Invoke or resume a compiled graph for the given session thread."""
    return graph.invoke(state, thread_config(session_id))


def update_graph_state(
    graph: CompiledStateGraph,
    session_id: str,
    values: dict[str, Any],
) -> None:
    graph.update_state(thread_config(session_id), values)


def get_graph_values(
    graph: CompiledStateGraph,
    session_id: str,
) -> dict[str, Any] | None:
    snapshot = graph.get_state(thread_config(session_id))
    if snapshot is None or not snapshot.values:
        return None
    return dict(snapshot.values)
