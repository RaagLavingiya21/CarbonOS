"""Scope-3 SBTi/FLAG target routes (Epic D). Orchestrate only — the wizard math
lives in s3_targets, Category A/B + coverage in s3_obligations.sbti_readiness,
inventory datapoints in db.s3_inventory_store, company profile in
db.s3_obligation_store, persistence in db.s3_target_store. org_id resolved here.

Base path `/scope-3`. Ships dark. Written but NOT yet run against a live DB.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

import db.s3_inventory_store as inv_store
import db.s3_obligation_store as obl_store
import db.s3_target_store as store
from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope3_schemas import (
    AmbitionDTO,
    DraftTargetDTO,
    FlagDTO,
    TargetDTO,
    TargetWizardRequest,
    TrajectoryPointDTO,
)
from db.org_store import get_active_org
from s3_obligations.models import ObligationProfile
from s3_targets.models import DraftTarget
from s3_targets.wizard import build_draft_target

router = APIRouter(tags=["scope3-targets"])


def _org_id(current_user: CurrentUser) -> str:
    org = get_active_org(current_user.access_token, user_id=current_user.user_id)
    if org is None:
        raise HTTPException(status_code=400, detail="No active organization for this user.")
    return org.id


def _profile(current_user: CurrentUser, org_id: str) -> ObligationProfile:
    row = obl_store.get_company_profile(access_token=current_user.access_token, org_id=org_id)
    if row is None:
        raise HTTPException(status_code=404, detail="No company profile — create one first.")
    return ObligationProfile(
        annual_revenue_usd=row.get("annual_revenue_usd"),
        employee_count=row.get("employee_count"),
        is_us_entity=bool(row.get("is_us_entity")),
        does_business_in_ca=bool(row.get("does_business_in_ca")),
        eu_turnover_eur=row.get("eu_turnover_eur"),
        eu_subsidiary=bool(row.get("eu_subsidiary")),
        eu_branch_turnover_eur=row.get("eu_branch_turnover_eur"),
        listed_jurisdictions=row.get("listed_jurisdictions") or [],
        sector=row.get("sector") or "",
        is_flag_sector=bool(row.get("is_flag_sector")),
        key_customers=row.get("key_customers") or [],
    )


def _categories(current_user: CurrentUser, inventory_id: int) -> dict[int, float]:
    rows = inv_store.list_category_results(
        access_token=current_user.access_token, inventory_id=inventory_id
    )
    return {int(c["scope3_category"]): float(c["total_kg_co2e"] or 0) for c in rows}


def _compute(current_user: CurrentUser, org_id: str, body: TargetWizardRequest) -> DraftTarget:
    return build_draft_target(
        _profile(current_user, org_id),
        _categories(current_user, body.inventory_id),
        base_year=body.base_year,
        target_year=body.target_year,
        reduction_pct=body.reduction_pct,
        method=body.method,
        covered_categories=set(body.covered_categories),
        version=body.version,
        horizon=body.horizon,
        sector=body.sector,
        flag_kg_co2e=body.flag_kg_co2e,
    )


def _draft_dto(dt: DraftTarget) -> DraftTargetDTO:
    r = dt.readiness
    return DraftTargetDTO(
        version=dt.version,
        horizon=dt.horizon,
        category_class=r.category_class,
        scope3_target_mandatory=r.scope3_target_mandatory,
        base_year_assurance_required=r.base_year_assurance_required,
        total_scope3_kg=r.total_scope3_kg,
        required_categories=r.required_categories,
        coverage_gap=r.coverage_gap,
        meets_requirement=r.meets_requirement,
        trajectory=[
            TrajectoryPointDTO(year=p.year, target_kg_co2e=p.target_kg_co2e)
            for p in dt.trajectory.points
        ],
        ambition=AmbitionDTO(
            chosen_reduction_pct=dt.ambition.chosen_reduction_pct,
            reference_reduction_pct=dt.ambition.reference_reduction_pct,
            meets_reference=dt.ambition.meets_reference,
            note=dt.ambition.note,
        ),
        flag=_flag_dto(dt),
        notes=dt.notes,
    )


def _flag_dto(dt: DraftTarget) -> FlagDTO | None:
    if dt.flag is None:
        return None
    return FlagDTO(
        is_flag_required=dt.flag.is_flag_required,
        flag_share=dt.flag.flag_share,
        reason=dt.flag.reason,
        no_deforestation_commitment_date=dt.flag.no_deforestation_commitment_date,
    )


@router.post("/scope-3/targets/wizard", response_model=DraftTargetDTO)
def target_wizard(
    body: TargetWizardRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> DraftTargetDTO:
    """Preview a conformant draft target (no persistence)."""
    return _draft_dto(_compute(current_user, _org_id(current_user), body))


@router.post("/scope-3/targets", response_model=TargetDTO)
def create_target(
    body: TargetWizardRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> TargetDTO:
    """Compute the draft and persist it (target + category coverage + FLAG)."""
    org_id = _org_id(current_user)
    dt = _compute(current_user, org_id, body)
    r = dt.readiness

    target = store.create_target(
        access_token=current_user.access_token,
        org_id=org_id,
        user_id=current_user.user_id,
        fields={
            "type": body.horizon,
            "method": body.method,
            "sbti_version": body.version,
            "base_year": body.base_year,
            "target_year": body.target_year,
            "reduction_pct": body.reduction_pct,
            "inventory_base_id": body.inventory_id,
            "assurance_required": r.base_year_assurance_required,
        },
    )
    store.replace_target_categories(
        access_token=current_user.access_token,
        org_id=org_id,
        target_id=target["target_id"],
        rows=[
            {
                "category_num": c.scope3_category,
                "pct_of_scope3": c.pct_of_scope3,
                "requires_coverage": c.requires_coverage,
                "is_covered": c.is_covered,
            }
            for c in r.category_coverage
        ],
    )
    if dt.flag and dt.flag.is_flag_required:
        store.upsert_flag_target(
            access_token=current_user.access_token,
            org_id=org_id,
            target_id=target["target_id"],
            fields={
                "flag_share_pct": dt.flag.flag_share,
                "flag_target_type": dt.flag.reason[:200],
                "no_deforestation_commitment_date": dt.flag.no_deforestation_commitment_date,
            },
        )
    return TargetDTO(**target)


@router.get("/scope-3/targets", response_model=list[TargetDTO])
def list_targets(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[TargetDTO]:
    rows = store.list_targets(access_token=current_user.access_token, org_id=_org_id(current_user))
    return [TargetDTO(**r) for r in rows]
