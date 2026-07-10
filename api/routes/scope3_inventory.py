"""Scope-3 corporate inventory routes (Epic A). Orchestrate only — parsing,
classification and aggregation live in s3_measure; persistence in
db.s3_inventory_store. org_id is resolved here (route layer) and passed down.

Base path `/scope-3` per the module URL convention. Ships behind
NEXT_PUBLIC_SCOPE3_ENABLED (nav hidden until GA).

NOTE: written but NOT yet run against a live DB ("write code now, apply later").
Verify once migrations 300-303 are applied to an isolated database.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

import db.s3_inventory_store as store
from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope3_schemas import (
    CategoryResultDTO,
    CreateInventoryRequest,
    InventoryDetailDTO,
    InventoryVersionDTO,
    SpendImportResponse,
)
from db.org_store import get_active_org
from s3_measure.inventory import build_inventory_from_spend
from s3_measure.spend_parser import ParsedSpend, SpendLine, parse_spend_csv

router = APIRouter(tags=["scope3-inventory"])

# Emission-factor library version stamped on each category rollup. Persisting it
# lets Epic E progress decomposition attribute EF-version changes (not just
# method switches) as method-driven change. Matches the vendored s3_factors
# dataset (Open CEDA 2025) and the DB default on s3_inventory_category_results.
EF_VERSION = "CEDA-2025"


def _org_id(current_user: CurrentUser) -> str:
    org = get_active_org(current_user.access_token, user_id=current_user.user_id)
    if org is None:
        raise HTTPException(status_code=400, detail="No active organization for this user.")
    return org.id


def _require_version(current_user: CurrentUser, inventory_id: int) -> dict:
    version = store.get_inventory_version(
        access_token=current_user.access_token, inventory_id=inventory_id
    )
    if version is None:
        raise HTTPException(status_code=404, detail=f"Inventory {inventory_id} not found.")
    return version


@router.post("/scope-3/inventory", response_model=InventoryVersionDTO)
def create_inventory(
    body: CreateInventoryRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> InventoryVersionDTO:
    version = store.create_inventory_version(
        access_token=current_user.access_token,
        org_id=_org_id(current_user),
        user_id=current_user.user_id,
        reporting_year=body.reporting_year,
        boundary_approach=body.boundary_approach,
    )
    return InventoryVersionDTO(**version)


@router.get("/scope-3/inventory", response_model=list[InventoryVersionDTO])
def list_inventory(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[InventoryVersionDTO]:
    rows = store.list_inventory_versions(
        access_token=current_user.access_token, org_id=_org_id(current_user)
    )
    return [InventoryVersionDTO(**r) for r in rows]


@router.post("/scope-3/inventory/{inventory_id}/spend/import", response_model=SpendImportResponse)
async def import_spend(
    inventory_id: int,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> SpendImportResponse:
    version = _require_version(current_user, inventory_id)
    if version["status"] == "locked":
        raise HTTPException(status_code=409, detail="Inventory is locked; create a new version.")

    content = await file.read()
    parsed = parse_spend_csv(content)
    if not parsed.is_valid:
        raise HTTPException(status_code=422, detail="; ".join(parsed.file_errors))

    records = [_line_to_record(line, file.filename) for line in parsed.rows]
    store.insert_spend_records(
        access_token=current_user.access_token,
        org_id=version["org_id"],
        inventory_id=inventory_id,
        user_id=current_user.user_id,
        records=records,
    )
    return SpendImportResponse(
        inventory_id=inventory_id,
        parsed_rows=len(parsed.rows),
        flagged_rows=len(parsed.flagged_row_indices),
        file_errors=parsed.file_errors,
    )


@router.post("/scope-3/inventory/{inventory_id}/calculate", response_model=InventoryDetailDTO)
def calculate_inventory(
    inventory_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> InventoryDetailDTO:
    version = _require_version(current_user, inventory_id)
    if version["status"] == "locked":
        raise HTTPException(status_code=409, detail="Inventory is locked.")

    records = store.list_spend_records(
        access_token=current_user.access_token, inventory_id=inventory_id
    )
    parsed = _records_to_parsed(records)
    result = build_inventory_from_spend(parsed)

    category_rows = [
        {
            "scope3_category": c.scope3_category,
            "method": c.method,
            "ef_version": EF_VERSION,
            "total_kg_co2e": c.total_kg_co2e,
            "line_count": c.line_count,
        }
        for c in result.category_results
    ]
    store.upsert_category_results(
        access_token=current_user.access_token,
        org_id=version["org_id"],
        inventory_id=inventory_id,
        results=category_rows,
    )
    store.set_inventory_total(
        access_token=current_user.access_token,
        inventory_id=inventory_id,
        total_kg_co2e=result.total_kg_co2e,
    )
    return _detail(current_user, inventory_id)


@router.get("/scope-3/inventory/{inventory_id}", response_model=InventoryDetailDTO)
def get_inventory(
    inventory_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> InventoryDetailDTO:
    _require_version(current_user, inventory_id)
    return _detail(current_user, inventory_id)


@router.post("/scope-3/inventory/{inventory_id}/lock", response_model=InventoryVersionDTO)
def lock_inventory(
    inventory_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> InventoryVersionDTO:
    _require_version(current_user, inventory_id)
    locked = store.lock_inventory_version(
        access_token=current_user.access_token, inventory_id=inventory_id
    )
    return InventoryVersionDTO(**locked)


# --- helpers ----------------------------------------------------------------


def _line_to_record(line: SpendLine, source_file: str | None) -> dict:
    flag = line.flags[0].flag_type if line.flags else "ok"
    return {
        "gl_account": line.gl_account,
        "description": line.description,
        "vendor": line.vendor,
        "amount_usd": line.amount_usd,
        "currency": line.currency,
        "period": line.period,
        "flag_status": flag,
        "source_file": source_file,
    }


def _records_to_parsed(records: list[dict]) -> ParsedSpend:
    lines = [
        SpendLine(
            row_index=i,
            description=r.get("description"),
            amount_usd=r.get("amount_usd"),
            gl_account=r.get("gl_account"),
            vendor=r.get("vendor"),
            period=r.get("period"),
            currency=r.get("currency"),
            flags=[],
        )
        for i, r in enumerate(records)
    ]
    return ParsedSpend(rows=lines, file_errors=[])


def _detail(current_user: CurrentUser, inventory_id: int) -> InventoryDetailDTO:
    version = store.get_inventory_version(
        access_token=current_user.access_token, inventory_id=inventory_id
    )
    categories = store.list_category_results(
        access_token=current_user.access_token, inventory_id=inventory_id
    )
    return InventoryDetailDTO(
        version=InventoryVersionDTO(**version),
        categories=[
            CategoryResultDTO(
                scope3_category=c["scope3_category"],
                method=c["method"],
                total_kg_co2e=c["total_kg_co2e"],
                line_count=c["line_count"],
                notes=c.get("notes"),
            )
            for c in categories
        ],
    )
