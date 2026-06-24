"""LangGraph StateGraph for the Scope 3 Gap Analyzer workflow."""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from api.graphs.checkpointer import get_checkpointer
from api.graphs.helpers import get_graph_values, invoke_graph, update_graph_state
from gap_analyzer.executor import execute_step
from gap_analyzer.models import CompanyProfile, Plan, ToolResult
from gap_analyzer.planner import generate_plan

GapPhase = Literal["planning", "executing", "checkpoint", "done"]


class GapAnalyzerState(TypedDict, total=False):
    session_id: str
    profile: CompanyProfile
    plan: Plan | None
    current_step: int
    results: dict[str, ToolResult]
    call_counts: dict[str, int]
    phase: GapPhase
    result: ToolResult | None
    approval_action: Literal["continue", "stop"] | None


def _plan_node(state: GapAnalyzerState) -> dict:
    profile = state["profile"]
    session_id = state["session_id"]
    plan = generate_plan(profile, session_id=session_id)
    return {
        "plan": plan,
        "phase": "planning",
        "current_step": 0,
        "results": {},
        "call_counts": {},
        "result": None,
        "approval_action": None,
    }


def _execute_tool_node(state: GapAnalyzerState) -> dict:
    plan = state["plan"]
    profile = state["profile"]
    current_step = state.get("current_step", 0)
    session_id = state["session_id"]

    if plan is None or current_step >= len(plan.steps):
        return {"phase": "done"}

    step = plan.steps[current_step]
    results = dict(state.get("results", {}))
    call_counts = dict(state.get("call_counts", {}))

    result = execute_step(
        step=step,
        company_profile=profile,
        previous_results=results,
        call_counts=call_counts,
        session_id=session_id,
    )
    results[step.tool_name] = result

    has_stopping_error = result.error == "infinite_loop_guard" or (
        result.error is not None and result.error != "not_implemented"
    )

    updates: dict = {
        "result": result,
        "results": results,
        "call_counts": call_counts,
    }

    if has_stopping_error or step.has_checkpoint_after:
        updates["phase"] = "checkpoint"
    else:
        next_step = current_step + 1
        updates["current_step"] = next_step
        updates["phase"] = "done" if next_step >= len(plan.steps) else "executing"

    return updates


def _human_review_node(state: GapAnalyzerState) -> dict:
    action = state.get("approval_action", "continue")
    plan = state["plan"]
    current_step = state.get("current_step", 0)

    if action == "stop":
        return {"phase": "done", "approval_action": None}

    next_step = current_step + 1
    phase: GapPhase = "done" if next_step >= len(plan.steps) else "executing"
    return {
        "current_step": next_step,
        "phase": phase,
        "approval_action": None,
    }


def _save_results_node(state: GapAnalyzerState) -> dict:
    return {"phase": "done"}


def _route_after_execute(state: GapAnalyzerState) -> str:
    plan = state.get("plan")
    current_step = state.get("current_step", 0)
    result = state.get("result")

    if plan is None or current_step >= len(plan.steps):
        return "save_results"

    step = plan.steps[current_step]
    has_stopping_error = result is not None and (
        result.error == "infinite_loop_guard"
        or (result.error is not None and result.error != "not_implemented")
    )
    if has_stopping_error or step.has_checkpoint_after:
        return "human_review"

    if current_step >= len(plan.steps):
        return "save_results"
    return "execute_tool"


def _route_after_human_review(state: GapAnalyzerState) -> str:
    plan = state.get("plan")
    current_step = state.get("current_step", 0)
    if state.get("phase") == "done":
        return "save_results"
    if plan is None or current_step >= len(plan.steps):
        return "save_results"
    return "execute_tool"


def _build_gap_analyzer_graph():
    builder = StateGraph(GapAnalyzerState)
    builder.add_node("plan", _plan_node)
    builder.add_node("execute_tool", _execute_tool_node)
    builder.add_node("human_review", _human_review_node)
    builder.add_node("save_results", _save_results_node)

    builder.add_edge(START, "plan")
    builder.add_edge("plan", "execute_tool")
    builder.add_conditional_edges(
        "execute_tool",
        _route_after_execute,
        {
            "human_review": "human_review",
            "execute_tool": "execute_tool",
            "save_results": "save_results",
        },
    )
    builder.add_conditional_edges(
        "human_review",
        _route_after_human_review,
        {
            "execute_tool": "execute_tool",
            "save_results": "save_results",
        },
    )
    builder.add_edge("save_results", END)

    return builder.compile(
        checkpointer=get_checkpointer(),
        interrupt_before=["execute_tool", "human_review"],
    )


_gap_analyzer_graph = None


def get_gap_analyzer_graph():
    global _gap_analyzer_graph
    if _gap_analyzer_graph is None:
        _gap_analyzer_graph = _build_gap_analyzer_graph()
    return _gap_analyzer_graph


def start_gap_analysis(session_id: str, profile: CompanyProfile) -> GapAnalyzerState:
    """Run the planner node and pause before the first tool execution."""
    graph = get_gap_analyzer_graph()
    initial: GapAnalyzerState = {
        "session_id": session_id,
        "profile": profile,
        "plan": None,
        "current_step": 0,
        "results": {},
        "call_counts": {},
        "phase": "planning",
        "result": None,
        "approval_action": None,
    }
    return invoke_graph(graph, session_id, initial)


def execute_gap_step(session_id: str) -> GapAnalyzerState:
    """Resume graph execution for the next tool step."""
    graph = get_gap_analyzer_graph()
    return invoke_graph(graph, session_id, None)


def approve_gap_checkpoint(
    session_id: str,
    action: Literal["continue", "stop"],
) -> GapAnalyzerState:
    """Resume from a human-review checkpoint with continue or stop."""
    graph = get_gap_analyzer_graph()
    update_graph_state(graph, session_id, {"approval_action": action})
    return invoke_graph(graph, session_id, None)


def get_gap_state(session_id: str) -> GapAnalyzerState | None:
    return get_graph_values(get_gap_analyzer_graph(), session_id)
