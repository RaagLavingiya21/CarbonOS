"""Scope 2 reporting routes — "one number, many formats" (PRD 5.5).

From one persisted calculation, generate a prefilled response for a destination
(standard summary, CDP Supply Chain, Amazon Supply Chain) plus a CSV. Mappings are
config in s2_reporting.formats, so buyer/CDP template drift is a data change.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope2_schemas import (
    BuyerRequestDTO,
    CreateBuyerRequest,
    ReportDestinationDTO,
    ReportResponse,
    ReportRow,
    UpdateBuyerRequest,
)
from api.routes.scope2_deps import resolve_org_id
from db import (
    org_store,
    s2_bill_store,
    s2_buyer_request_store,
    s2_calc_store,
    s2_site_store,
)
from s2_quality.scoring import compute_coverage
from s2_reporting.formats import (
    DESTINATIONS,
    UnknownDestinationError,
    build_report,
    report_to_csv,
)
from s2_reporting.summary import build_summary

router = APIRouter(prefix="/api/scope2", tags=["scope2"])

_DESTINATION_LABELS = {
    "standard": "Standard summary",
    "cdp": "CDP Supply Chain",
    "amazon": "Amazon Supply Chain",
}


@router.get("/report-destinations", response_model=list[ReportDestinationDTO])
def list_report_destinations(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[ReportDestinationDTO]:
    return [
        ReportDestinationDTO(key=key, label=_DESTINATION_LABELS.get(key, key))
        for key in DESTINATIONS
    ]


@router.get("/calculations/{calc_id}/report", response_model=ReportResponse)
def get_report(
    calc_id: int,
    destination: str = Query("standard"),
    current_user: CurrentUser = Depends(get_current_user),
) -> ReportResponse:
    token = current_user.access_token
    calc = s2_calc_store.get_calculation(calc_id, token)
    if calc is None:
        raise HTTPException(status_code=404, detail=f"Calculation {calc_id} not found.")

    org = org_store.get_active_org(token, user_id=current_user.user_id)
    entity = org.name if org else "Reporting entity"

    site_ids = [
        int(site["site_id"])
        for site in s2_site_store.list_sites(token)
        if not site.get("franchise_flag")
    ]
    coverage = compute_coverage(s2_bill_store.list_active_bills(token), site_ids)
    summary = build_summary(
        calc, entity=entity, coverage_fraction=coverage.coverage_fraction
    )

    try:
        rows = build_report(summary, destination)
    except UnknownDestinationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return ReportResponse(
        destination=destination,
        entity=entity,
        reporting_year=summary.reporting_year,
        rows=[ReportRow(field=r["field"], value=str(r["value"])) for r in rows],
        csv=report_to_csv(rows),
    )


# --- inbound buyer/CDP request queue ---------------------------------------


@router.post("/buyer-requests", response_model=BuyerRequestDTO, status_code=201)
def create_buyer_request(
    request: CreateBuyerRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> BuyerRequestDTO:
    org_id = resolve_org_id(current_user)
    request_id = s2_buyer_request_store.create_request(
        request.model_dump(exclude_none=True),
        org_id=org_id,
        user_id=current_user.user_id,
        access_token=current_user.access_token,
    )
    row = s2_buyer_request_store.get_request(request_id, current_user.access_token)
    if row is None:
        raise HTTPException(status_code=500, detail="Request created but not retrievable.")
    return BuyerRequestDTO.from_row(row)


@router.get("/buyer-requests", response_model=list[BuyerRequestDTO])
def list_buyer_requests(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[BuyerRequestDTO]:
    rows = s2_buyer_request_store.list_requests(current_user.access_token)
    return [BuyerRequestDTO.from_row(row) for row in rows]


@router.patch("/buyer-requests/{request_id}", response_model=BuyerRequestDTO)
def update_buyer_request(
    request_id: int,
    request: UpdateBuyerRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> BuyerRequestDTO:
    existing = s2_buyer_request_store.get_request(request_id, current_user.access_token)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found.")
    updates = request.model_dump(exclude_none=True)
    if updates.get("status") == "answered" and not existing.get("answered_at"):
        updates.setdefault(
            "answered_at", datetime.now(timezone.utc).isoformat()
        )
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    row = s2_buyer_request_store.update_request(
        request_id, updates, access_token=current_user.access_token
    )
    return BuyerRequestDTO.from_row(row or existing)


@router.delete("/buyer-requests/{request_id}", status_code=204)
def delete_buyer_request(
    request_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    try:
        s2_buyer_request_store.delete_request(
            request_id, access_token=current_user.access_token
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
