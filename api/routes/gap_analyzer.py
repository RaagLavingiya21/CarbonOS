"""FastAPI routes for the Scope 3 gap analyzer workflow."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

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
from gap_analyzer import execute_step, generate_plan
from gap_analyzer.models import CompanyProfile, Plan, ToolResult

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
    plan = generate_plan(profile, session_id=session.session_id)
    session_store.update(session.session_id, plan=plan)
    return GapPlanResponse(
        session_id=session.session_id,
        phase="planning",
        profile=CompanyProfileDTO.from_domain(profile),
        plan=PlanDTO.from_domain(plan),
        current_step=0,
    )


@router.post("/api/gap-analysis/execute", response_model=GapExecuteResponse)
def execute_gap_step(request: GapExecuteRequest) -> GapExecuteResponse:
    session = _session_or_404(request.session_id)
    profile: CompanyProfile | None = session.data.get("profile")
    plan: Plan | None = session.data.get("plan")
    current_step: int = session.data.get("current_step", 0)
    results: dict[str, ToolResult] = session.data.get("results", {})
    call_counts: dict[str, int] = session.data.get("call_counts", {})

    if profile is None or plan is None:
        raise HTTPException(status_code=409, detail="No generated gap analysis plan found.")
    if current_step >= len(plan.steps):
        session_store.update(session.session_id, phase="done", current_step=current_step)
        return GapExecuteResponse(
            session_id=session.session_id,
            phase="done",
            current_step=current_step,
            results=_results_dto(results),
        )

    step = plan.steps[current_step]
    result = execute_step(
        step=step,
        company_profile=profile,
        previous_results=results,
        call_counts=call_counts,
        session_id=session.session_id,
    )
    results = dict(results)
    results[step.tool_name] = result

    has_stopping_error = result.error == "infinite_loop_guard" or (
        result.error and result.error != "not_implemented"
    )
    if has_stopping_error:
        phase = "checkpoint"
    elif step.has_checkpoint_after:
        phase = "checkpoint"
    else:
        current_step += 1
        phase = "done" if current_step >= len(plan.steps) else "executing"

    session_store.update(
        session.session_id,
        phase=phase,
        current_step=current_step,
        results=results,
        call_counts=call_counts,
    )
    return GapExecuteResponse(
        session_id=session.session_id,
        phase=phase,
        current_step=current_step,
        result=ToolResultDTO.from_domain(result),
        results=_results_dto(results),
    )


@router.post("/api/gap-analysis/approve", response_model=GapApproveResponse)
def approve_gap_checkpoint(request: GapApproveRequest) -> GapApproveResponse:
    session = _session_or_404(request.session_id)
    plan: Plan | None = session.data.get("plan")
    current_step: int = session.data.get("current_step", 0)
    if plan is None:
        raise HTTPException(status_code=409, detail="No generated gap analysis plan found.")

    if request.action == "stop":
        phase = "done"
    else:
        current_step += 1
        phase = "done" if current_step >= len(plan.steps) else "executing"

    session_store.update(session.session_id, phase=phase, current_step=current_step)
    return GapApproveResponse(
        session_id=session.session_id,
        phase=phase,
        current_step=current_step,
    )


@router.get("/api/gap-analysis/sessions/{session_id}/report", response_model=GapReportResponse)
def get_gap_report(session_id: str) -> GapReportResponse:
    session = _session_or_404(session_id)
    profile: CompanyProfile | None = session.data.get("profile")
    results: dict[str, ToolResult] = session.data.get("results", {})
    if profile is None:
        raise HTTPException(status_code=409, detail="No company profile found for this session.")
    return GapReportResponse(
        session_id=session.session_id,
        profile=CompanyProfileDTO.from_domain(profile),
        markdown=_compile_report(profile, results),
        results=_results_dto(results),
    )
