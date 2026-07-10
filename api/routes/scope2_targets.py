"""Scope 2 target-setting routes — SBTi-style reduction trajectories (migration 049).

Users set a base-year total + a future target (amount or % reduction). The calc
engine can flag progress as on-track / off-track vs. trajectory.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope2_schemas import CreateTargetRequest, TargetDTO
from api.routes.scope2_deps import resolve_org_id
from db import s2_targets_store

router = APIRouter(prefix="/api/scope2", tags=["scope2"])


@router.get("/targets", response_model=list[TargetDTO])
def list_targets(current_user: CurrentUser = Depends(get_current_user)) -> list[TargetDTO]:
    """All targets for the user's org."""
    org_id = resolve_org_id(current_user)
    return [
        TargetDTO.from_row(row)
        for row in s2_targets_store.list_targets(org_id, current_user.access_token)
    ]


@router.get("/targets/active", response_model=TargetDTO | None)
def get_active_target(current_user: CurrentUser = Depends(get_current_user)) -> TargetDTO | None:
    """The currently active target for the org (if any)."""
    org_id = resolve_org_id(current_user)
    row = s2_targets_store.get_active_target(org_id, current_user.access_token)
    return TargetDTO.from_row(row) if row else None


@router.post("/targets", response_model=TargetDTO, status_code=201)
def create_target(
    request: CreateTargetRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> TargetDTO:
    """Create a new target."""
    if request.target_amount_tco2e is None and request.target_pct_reduction is None:
        raise HTTPException(
            status_code=422,
            detail="Either target_amount_tco2e or target_pct_reduction must be set.",
        )
    if request.target_year <= request.base_year:
        raise HTTPException(status_code=422, detail="target_year must be later than base_year.")

    org_id = resolve_org_id(current_user)
    target_id = s2_targets_store.create_target(
        request.model_dump(exclude_none=True),
        org_id=org_id,
        user_id=current_user.user_id,
        access_token=current_user.access_token,
    )
    row = s2_targets_store.get_target(target_id, current_user.access_token)
    if row is None:
        raise HTTPException(status_code=500, detail="Target created but not retrievable.")
    return TargetDTO.from_row(row)


@router.patch("/targets/{target_id}", response_model=TargetDTO)
def update_target(
    target_id: int,
    updates: dict,
    current_user: CurrentUser = Depends(get_current_user),
) -> TargetDTO:
    """Update target metadata (status, notes); not totals."""
    s2_targets_store.update_target(target_id, updates, access_token=current_user.access_token)
    row = s2_targets_store.get_target(target_id, current_user.access_token)
    if row is None:
        raise HTTPException(status_code=404, detail="Target not found.")
    return TargetDTO.from_row(row)


@router.delete("/targets/{target_id}", status_code=204)
def delete_target(
    target_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    s2_targets_store.delete_target(target_id, access_token=current_user.access_token)
