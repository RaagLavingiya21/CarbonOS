"""Scope 2 reporting routes — "one number, many formats" (PRD 5.5).

From one persisted calculation, generate a prefilled response for a destination
(standard summary, CDP Supply Chain, Amazon Supply Chain) plus a CSV. Mappings are
config in s2_reporting.formats, so buyer/CDP template drift is a data change.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope2_schemas import (
    ReportDestinationDTO,
    ReportResponse,
    ReportRow,
)
from db import org_store, s2_bill_store, s2_calc_store, s2_site_store
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
