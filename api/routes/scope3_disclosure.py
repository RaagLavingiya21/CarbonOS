"""Scope-3 disclosure routes (Epic G / P.4.1). Orchestrate only — datapoint
mapping lives in s3_disclosure, inventory datapoints in db.s3_inventory_store.
org_id resolved here. Base path `/scope-3`. Ships dark.

Reads a locked/calculated Epic A inventory and maps it onto a framework's
Scope-3 datapoints (ESRS E1 / SB253 / IFRS S2). Numbers are looked up from the
inventory; SB253 is emitted provisional. Written but NOT yet run against a live
DB (verify once migrations are applied).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response

import db.s3_inventory_store as inv_store
from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope3_schemas import (
    DisclosureCalcRequest,
    DisclosureDatapointDTO,
    DisclosureResultDTO,
)
from s3_disclosure.mapper import DisclosureSpecError, available_frameworks, map_disclosure
from s3_disclosure.models import DisclosureResult
from s3_disclosure.serialize import to_csv, to_markdown

router = APIRouter(tags=["scope3-disclosure"])


@router.get("/scope-3/disclosures/frameworks", response_model=list[str])
def list_frameworks() -> list[str]:
    return available_frameworks()


@router.post("/scope-3/disclosures/calculate", response_model=DisclosureResultDTO)
def calculate_disclosure(
    body: DisclosureCalcRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> DisclosureResultDTO:
    result = _map(current_user, body.inventory_id, body.framework)
    return _to_dto(result)


@router.get("/scope-3/disclosures/export")
def export_disclosure(
    inventory_id: int,
    framework: str,
    format: str = Query("markdown", pattern="^(csv|markdown|md)$"),
    current_user: CurrentUser = Depends(get_current_user),
) -> Response:
    result = _map(current_user, inventory_id, framework)
    content = to_csv(result) if format == "csv" else to_markdown(result)
    ext = "csv" if format == "csv" else "md"
    media = "text/csv" if format == "csv" else "text/markdown"
    return Response(
        content=content,
        media_type=media,
        headers={
            "Content-Disposition": f"attachment; filename=scope3_{framework}_{inventory_id}.{ext}"
        },
    )


# --- helpers ----------------------------------------------------------------


def inventory_from_rows(version: dict, categories: list[dict]) -> dict:
    """Shape the stored inventory version + category rows into the dict the
    disclosure mapper expects. Pure — unit-testable without a DB."""
    return {
        "total": version.get("total_kg_co2e"),
        "categories": {
            int(c["scope3_category"]): float(c["total_kg_co2e"] or 0) for c in categories
        },
    }


def _map(current_user: CurrentUser, inventory_id: int, framework: str) -> DisclosureResult:
    version = inv_store.get_inventory_version(
        access_token=current_user.access_token, inventory_id=inventory_id
    )
    if version is None:
        raise HTTPException(status_code=404, detail=f"Inventory {inventory_id} not found.")
    categories = inv_store.list_category_results(
        access_token=current_user.access_token, inventory_id=inventory_id
    )
    try:
        return map_disclosure(inventory_from_rows(version, categories), framework)
    except DisclosureSpecError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _to_dto(result: DisclosureResult) -> DisclosureResultDTO:
    def dp(d) -> DisclosureDatapointDTO:
        return DisclosureDatapointDTO(
            key=d.key,
            label=d.label,
            value=d.value,
            text=d.text,
            unit=d.unit,
            source_ref=d.source_ref,
            flag=d.flag,
        )

    return DisclosureResultDTO(
        framework=result.framework,
        format_version=result.format_version,
        is_provisional=result.is_provisional,
        datapoints=[dp(d) for d in result.datapoints],
        category_breakdown=[dp(d) for d in result.category_breakdown],
        notes=result.notes,
    )
