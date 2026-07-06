"""Scope 2 leased-site landlord data-request routes (PRD 5.2).

Track outreach to landlords for whole-building / sub-metered data on
landlord-metered leased sites: create a request, work its status
(draft -> sent -> responded/declined), and record the returned data reference.
Status transitions stamp sent_at / responded_at automatically.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope2_schemas import (
    CreateLandlordRequest,
    LandlordRequestDTO,
    UpdateLandlordRequest,
)
from api.routes.scope2_deps import resolve_org_id
from db import s2_landlord_store

router = APIRouter(prefix="/api/scope2", tags=["scope2"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/landlord-requests", response_model=LandlordRequestDTO, status_code=201)
def create_landlord_request(
    request: CreateLandlordRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> LandlordRequestDTO:
    org_id = resolve_org_id(current_user)
    request_id = s2_landlord_store.create_request(
        request.model_dump(),
        org_id=org_id,
        user_id=current_user.user_id,
        access_token=current_user.access_token,
    )
    row = s2_landlord_store.get_request(request_id, current_user.access_token)
    if row is None:
        raise HTTPException(status_code=500, detail="Request created but not retrievable.")
    return LandlordRequestDTO.from_row(row)


@router.get("/landlord-requests", response_model=list[LandlordRequestDTO])
def list_landlord_requests(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[LandlordRequestDTO]:
    rows = s2_landlord_store.list_requests(current_user.access_token)
    return [LandlordRequestDTO.from_row(row) for row in rows]


@router.patch("/landlord-requests/{request_id}", response_model=LandlordRequestDTO)
def update_landlord_request(
    request_id: int,
    request: UpdateLandlordRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> LandlordRequestDTO:
    existing = s2_landlord_store.get_request(request_id, current_user.access_token)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found.")

    updates = request.model_dump(exclude_none=True)
    # Stamp lifecycle timestamps on the relevant status transitions.
    if updates.get("status") == "sent" and not existing.get("sent_at"):
        updates.setdefault("sent_at", _now())
    if updates.get("status") in {"responded", "declined"} and not existing.get(
        "responded_at"
    ):
        updates.setdefault("responded_at", _now())
    updates["updated_at"] = _now()

    row = s2_landlord_store.update_request(
        request_id, updates, access_token=current_user.access_token
    )
    return LandlordRequestDTO.from_row(row or existing)


@router.delete("/landlord-requests/{request_id}", status_code=204)
def delete_landlord_request(
    request_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    try:
        s2_landlord_store.delete_request(
            request_id, access_token=current_user.access_token
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
