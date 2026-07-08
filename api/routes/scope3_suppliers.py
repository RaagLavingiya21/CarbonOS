"""Scope-3 supplier routes (Epic F). Orchestrate only — cohorting + scorecard
math live in s3_suppliers; persistence in db.s3_supplier_store. org_id resolved
here. Base path `/scope-3`. Ships dark. NOT yet run against a live DB.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

import db.s3_supplier_store as store
from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope3_schemas import (
    CohortDTO,
    CohortRequest,
    SupplierCreateRequest,
    SupplierDTO,
    SupplierScorecardDTO,
)
from db.org_store import get_active_org
from s3_suppliers.cohorting import build_cohort
from s3_suppliers.models import Supplier
from s3_suppliers.scorecard import program_scorecard

router = APIRouter(tags=["scope3-suppliers"])

_SUPPLIER_FIELDS = (
    "name",
    "scope3_category",
    "emissions_kg",
    "spend_usd",
    "pcf_received",
    "dq_score",
    "supplier_sbt_status",
)


def _org_id(current_user: CurrentUser) -> str:
    org = get_active_org(current_user.access_token, user_id=current_user.user_id)
    if org is None:
        raise HTTPException(status_code=400, detail="No active organization for this user.")
    return org.id


def supplier_from_row(row: dict) -> Supplier:
    """Pure — unit-testable without a DB."""
    return Supplier(
        supplier_id=str(row["supplier_id"]),
        name=row["name"],
        scope3_category=int(row["scope3_category"]),
        emissions_kg=float(row.get("emissions_kg") or 0),
        spend_usd=float(row.get("spend_usd") or 0),
        pcf_received=bool(row.get("pcf_received")),
        dq_score=row.get("dq_score"),
        supplier_sbt_status=row.get("supplier_sbt_status") or "none",
    )


@router.post("/scope-3/suppliers", response_model=SupplierDTO)
def create_supplier(
    body: SupplierCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> SupplierDTO:
    row = store.create_supplier(
        access_token=current_user.access_token,
        org_id=_org_id(current_user),
        user_id=current_user.user_id,
        supplier={k: getattr(body, k) for k in _SUPPLIER_FIELDS},
    )
    return SupplierDTO(**row)


@router.get("/scope-3/suppliers", response_model=list[SupplierDTO])
def list_suppliers(current_user: CurrentUser = Depends(get_current_user)) -> list[SupplierDTO]:
    rows = store.list_suppliers(
        access_token=current_user.access_token, org_id=_org_id(current_user)
    )
    return [SupplierDTO(**r) for r in rows]


@router.delete("/scope-3/suppliers/{supplier_id}", status_code=204)
def delete_supplier(
    supplier_id: int, current_user: CurrentUser = Depends(get_current_user)
) -> None:
    store.delete_supplier(access_token=current_user.access_token, supplier_id=supplier_id)


@router.post("/scope-3/suppliers/cohort", response_model=CohortDTO)
def cohort(
    body: CohortRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> CohortDTO:
    org_id = _org_id(current_user)
    rows = store.list_suppliers(access_token=current_user.access_token, org_id=org_id)
    suppliers = [supplier_from_row(r) for r in rows]
    result = build_cohort(
        suppliers, set(body.hotspot_categories), top_n=body.top_n, basis=body.basis
    )
    return CohortDTO(
        basis=result.basis,
        hotspot_categories=result.hotspot_categories,
        emissions_covered_pct=result.emissions_covered_pct,
        members=[_supplier_dto(s, org_id) for s in result.members],
    )


@router.get("/scope-3/suppliers/scorecard", response_model=SupplierScorecardDTO)
def scorecard(current_user: CurrentUser = Depends(get_current_user)) -> SupplierScorecardDTO:
    rows = store.list_suppliers(
        access_token=current_user.access_token, org_id=_org_id(current_user)
    )
    sc = program_scorecard([supplier_from_row(r) for r in rows])
    return SupplierScorecardDTO(
        supplier_count=sc.supplier_count,
        pcf_coverage_pct=sc.pcf_coverage_pct,
        emissions_covered_pct=sc.emissions_covered_pct,
        avg_dq=sc.avg_dq,
        sbt_committed_count=sc.sbt_committed_count,
        sbt_validated_count=sc.sbt_validated_count,
    )


def _supplier_dto(s: Supplier, org_id: str) -> SupplierDTO:
    return SupplierDTO(
        supplier_id=int(s.supplier_id),
        org_id=org_id,
        name=s.name,
        scope3_category=s.scope3_category,
        emissions_kg=s.emissions_kg,
        spend_usd=s.spend_usd,
        pcf_received=s.pcf_received,
        dq_score=s.dq_score,
        supplier_sbt_status=s.supplier_sbt_status,
    )
