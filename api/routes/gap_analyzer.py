"""FastAPI routes for the Scope 3 gap analyzer workflow."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.graphs.gap_analyzer_graph import (
    approve_gap_checkpoint,
    execute_gap_step,
    get_gap_state,
    start_gap_analysis,
)
from api.models.schemas import (
    CompanyProfileDTO,
    GapApproveRequest,
    GapApproveResponse,
    GapExecuteRequest,
    GapExecuteResponse,
    GapPlanRequest,
    GapPlanResponse,
    GapReportResponse,
    PlanDTO,
    ToolResultDTO,
)
from api.services.session_store import WorkflowSession, session_store
from gap_analyzer.models import CompanyProfile, ToolResult

router = APIRouter(tags=["gap-analysis"])


def _session_or_404(session_id: str) -> WorkflowSession:
    session = session_store.get(session_id, workflow="gap_analysis")
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Gap analysis session '{session_id}' not found.",
        )
    return session


def _results_dto(results: dict[str, ToolResult]) -> dict[str, ToolResultDTO]:
    return {name: ToolResultDTO.from_domain(result) for name, result in results.items()}


def _sync_session_from_graph(session_id: str, state: dict) -> None:
    session_store.update(
        session_id,
        phase=state.get("phase", "planning"),
        profile=state.get("profile"),
        plan=state.get("plan"),
        current_step=state.get("current_step", 0),
        results=state.get("results", {}),
        call_counts=state.get("call_counts", {}),
    )


def _compile_report(profile: CompanyProfile, results: dict[str, ToolResult]) -> str:
    lines = [
        "# Scope 3 Gap Analysis Report\n",
        f"**Company:** {profile.name}  ",
        f"**Sector:** {profile.sector}  ",
        f"**Geography:** {profile.geography}  ",
        f"**Size:** {profile.size}  ",
        f"**Products / services:** {profile.products}\n",
        "---\n",
    ]
    for tool_name, result in results.items():
        section_title = tool_name.replace("_", " ").title()
        if result.error == "not_implemented":
            lines.append(f"## {section_title}\n\n_{result.content}_\n")
        elif result.error:
            lines.append(f"## {section_title}\n\n**Error:** {result.error}\n")
        else:
            lines.append(f"## {section_title}\n\n{result.content}\n")
        if result.citations:
            lines.append("### Sources\n" + "\n".join(f"- {c}" for c in result.citations) + "\n")
    return "\n".join(lines)


@router.post("/api/gap-analysis/plan", response_model=GapPlanResponse)
def plan_gap_analysis(request: GapPlanRequest) -> GapPlanResponse:
    profile = request.profile.to_domain()
    session = session_store.create(
        "gap_analysis",
        "planning",
        profile=profile,
        current_step=0,
        results={},
        call_counts={},
    )
    state = start_gap_analysis(session.session_id, profile)
    _sync_session_from_graph(session.session_id, state)

    return GapPlanResponse(
        session_id=session.session_id,
        phase="planning",
        profile=CompanyProfileDTO.from_domain(profile),
        plan=PlanDTO.from_domain(state["plan"]),
        current_step=state.get("current_step", 0),
    )


@router.post("/api/gap-analysis/execute", response_model=GapExecuteResponse)
def execute_gap_step_route(request: GapExecuteRequest) -> GapExecuteResponse:
    session = _session_or_404(request.session_id)
    graph_state = get_gap_state(request.session_id)
    if graph_state is None:
        raise HTTPException(status_code=409, detail="No gap analysis graph state found.")

    plan = graph_state.get("plan")
    current_step = graph_state.get("current_step", 0)
    if plan is None:
        raise HTTPException(status_code=409, detail="No generated gap analysis plan found.")
    if current_step >= len(plan.steps) and graph_state.get("phase") == "done":
        return GapExecuteResponse(
            session_id=session.session_id,
            phase="done",
            current_step=current_step,
            results=_results_dto(graph_state.get("results", {})),
        )

    state = execute_gap_step(request.session_id)
    _sync_session_from_graph(session.session_id, state)

    return GapExecuteResponse(
        session_id=session.session_id,
        phase=state.get("phase", "executing"),
        current_step=state.get("current_step", 0),
        result=ToolResultDTO.from_domain(state["result"]) if state.get("result") else None,
        results=_results_dto(state.get("results", {})),
    )


@router.post("/api/gap-analysis/approve", response_model=GapApproveResponse)
def approve_gap_checkpoint_route(request: GapApproveRequest) -> GapApproveResponse:
    session = _session_or_404(request.session_id)
    graph_state = get_gap_state(request.session_id)
    if graph_state is None or graph_state.get("plan") is None:
        raise HTTPException(status_code=409, detail="No generated gap analysis plan found.")

    state = approve_gap_checkpoint(request.session_id, request.action)
    _sync_session_from_graph(session.session_id, state)

    return GapApproveResponse(
        session_id=session.session_id,
        phase=state.get("phase", "executing") if state.get("phase") != "done" else "done",
        current_step=state.get("current_step", 0),
    )


@router.get("/api/gap-analysis/sessions/{session_id}/report", response_model=GapReportResponse)
def get_gap_report(session_id: str) -> GapReportResponse:
    session = _session_or_404(session_id)
    graph_state = get_gap_state(session_id) or session.data
    profile: CompanyProfile | None = graph_state.get("profile")
    results: dict[str, ToolResult] = graph_state.get("results", {})
    if profile is None:
        raise HTTPException(status_code=409, detail="No company profile found for this session.")
    return GapReportResponse(
        session_id=session.session_id,
        profile=CompanyProfileDTO.from_domain(profile),
        markdown=_compile_report(profile, results),
        results=_results_dto(results),
    )
