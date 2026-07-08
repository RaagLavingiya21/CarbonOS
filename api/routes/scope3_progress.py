"""Scope-3 progress routes (Epic E). Orchestrate only — real-vs-method
decomposition, trajectory tracking and base-year recalc live in s3_progress;
inventories in db.s3_inventory_store; persistence in db.s3_progress_store.

Base path `/scope-3`. Ships dark. Written but NOT yet run against a live DB.

Note: the stored inventory schema carries per-category `method` but not an EF
version, so the route builds snapshots with a constant EF version — the
real-vs-method split therefore reflects method switches (spend↔activity↔
product_rollup) and completeness changes. Full EF-version attribution is a
follow-up (needs an ef_version column on category results).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

import db.s3_inventory_store as inv_store
import db.s3_progress_store as store
from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope3_schemas import (
    ProgressResultDTO,
    ProgressTrackRequest,
    RecalcRequest,
    RecalcResultDTO,
)
from db.org_store import get_active_org
from s3_progress.decompose import decompose
from s3_progress.models import CategoryPoint, InventorySnapshot
from s3_progress.tracker import evaluate_recalc, track_progress

router = APIRouter(tags=["scope3-progress"])

_EF_VERSION = "CEDA-2025"


def _org_id(current_user: CurrentUser) -> str:
    org = get_active_org(current_user.access_token, user_id=current_user.user_id)
    if org is None:
        raise HTTPException(status_code=400, detail="No active organization for this user.")
    return org.id


def snapshot_from_rows(version: dict, rows: list[dict]) -> InventorySnapshot:
    """Build an InventorySnapshot from a stored version + category rows. Pure —
    unit-testable without a DB."""
    return InventorySnapshot(
        reporting_year=int(version.get("reporting_year") or 0),
        categories=[
            CategoryPoint(
                scope3_category=int(r["scope3_category"]),
                kg_co2e=float(r["total_kg_co2e"] or 0),
                method=r.get("method") or "spend",
                ef_version=_EF_VERSION,
            )
            for r in rows
        ],
    )


def _snapshot(current_user: CurrentUser, inventory_id: int) -> InventorySnapshot:
    version = inv_store.get_inventory_version(
        access_token=current_user.access_token, inventory_id=inventory_id
    )
    if version is None:
        raise HTTPException(status_code=404, detail=f"Inventory {inventory_id} not found.")
    rows = inv_store.list_category_results(
        access_token=current_user.access_token, inventory_id=inventory_id
    )
    return snapshot_from_rows(version, rows)


@router.post("/scope-3/progress/track", response_model=ProgressResultDTO)
def track(
    body: ProgressTrackRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ProgressResultDTO:
    org_id = _org_id(current_user)
    base = _snapshot(current_user, body.base_inventory_id)
    current = _snapshot(current_user, body.current_inventory_id)
    decomposition = decompose(base, current)
    trajectory = {int(y): kg for y, kg in body.trajectory.items()}
    result = track_progress(decomposition, base.total_kg_co2e, trajectory)

    store.save_progress(
        access_token=current_user.access_token,
        org_id=org_id,
        user_id=current_user.user_id,
        fields={
            "target_id": body.target_id,
            "base_inventory_id": body.base_inventory_id,
            "current_inventory_id": body.current_inventory_id,
            "current_year": result.current_year,
            "actual_total_kg": result.actual_total_kg,
            "real_total_kg": result.real_total_kg,
            "method_delta_kg": result.method_delta_kg,
            "on_track": result.on_track,
        },
    )
    return ProgressResultDTO(
        current_year=result.current_year,
        base_total_kg=result.base_total_kg,
        real_total_kg=result.real_total_kg,
        actual_total_kg=result.actual_total_kg,
        trajectory_target_kg=result.trajectory_target_kg,
        on_track=result.on_track,
        method_delta_kg=result.method_delta_kg,
        notes=result.notes,
    )


@router.get("/scope-3/progress", response_model=list[dict])
def list_progress(current_user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return store.list_progress(access_token=current_user.access_token, org_id=_org_id(current_user))


@router.post("/scope-3/progress/recalc", response_model=RecalcResultDTO)
def recalc(
    body: RecalcRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> RecalcResultDTO:
    decision = (
        evaluate_recalc(body.trigger, body.significance_pct, threshold_pct=body.threshold_pct)
        if body.threshold_pct is not None
        else evaluate_recalc(body.trigger, body.significance_pct)
    )
    store.save_recalc(
        access_token=current_user.access_token,
        org_id=_org_id(current_user),
        user_id=current_user.user_id,
        fields={
            "trigger": decision.trigger,
            "significance_pct": decision.significance_pct,
            "threshold_pct": decision.threshold_pct,
            "recalc_required": decision.recalc_required,
            "rationale": decision.rationale,
        },
    )
    return RecalcResultDTO(
        trigger=decision.trigger,
        significance_pct=decision.significance_pct,
        threshold_pct=decision.threshold_pct,
        recalc_required=decision.recalc_required,
        rationale=decision.rationale,
    )
