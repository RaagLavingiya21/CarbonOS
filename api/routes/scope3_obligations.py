"""Scope-3 obligation front door routes (Epic C). Orchestrate only — the engine,
business-case, cascade and SBTi-readiness math live in s3_obligations;
persistence in db.s3_obligation_store. org_id resolved here and passed down.

Base path `/scope-3`. Ships dark behind NEXT_PUBLIC_SCOPE3_ENABLED.
Written but NOT yet run against a live DB ("write code now, apply later").
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException

import db.s3_inventory_store as inv_store
import db.s3_obligation_store as store
from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope3_schemas import (
    BusinessCaseDTO,
    CascadeSignalDTO,
    CompanyProfileRequest,
    DueItemDTO,
    EvaluationResponse,
    ObligationDTO,
    SBTiReadinessRequest,
    SBTiReadinessResponse,
    TimelineItemDTO,
)
from db.org_store import get_active_org
from s3_obligations.business_case import build_business_case
from s3_obligations.cascade import detect_cascade
from s3_obligations.engine import evaluate
from s3_obligations.models import Obligation, ObligationProfile
from s3_obligations.sbti_readiness import assess_sbti_readiness

router = APIRouter(tags=["scope3-obligations"])

_PROFILE_KEYS = (
    "annual_revenue_usd",
    "employee_count",
    "is_us_entity",
    "does_business_in_ca",
    "eu_turnover_eur",
    "eu_subsidiary",
    "eu_branch_turnover_eur",
    "listed_jurisdictions",
    "sector",
    "is_flag_sector",
    "key_customers",
)


def _org_id(current_user: CurrentUser) -> str:
    org = get_active_org(current_user.access_token, user_id=current_user.user_id)
    if org is None:
        raise HTTPException(status_code=400, detail="No active organization for this user.")
    return org.id


def _load_profile(current_user: CurrentUser, org_id: str) -> ObligationProfile:
    row = store.get_company_profile(access_token=current_user.access_token, org_id=org_id)
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


@router.post("/scope-3/company-profile")
def upsert_profile(
    body: CompanyProfileRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return store.upsert_company_profile(
        access_token=current_user.access_token,
        org_id=_org_id(current_user),
        user_id=current_user.user_id,
        profile={k: getattr(body, k) for k in _PROFILE_KEYS},
    )


@router.get("/scope-3/company-profile")
def get_profile(current_user: CurrentUser = Depends(get_current_user)) -> dict | None:
    return store.get_company_profile(
        access_token=current_user.access_token, org_id=_org_id(current_user)
    )


@router.post("/scope-3/obligations/evaluate", response_model=EvaluationResponse)
def evaluate_obligations(
    current_user: CurrentUser = Depends(get_current_user),
) -> EvaluationResponse:
    org_id = _org_id(current_user)
    profile = _load_profile(current_user, org_id)
    result = evaluate(profile)

    all_obligations = result.applicable + result.uncertain + result.not_applicable
    store.save_obligations(
        access_token=current_user.access_token,
        org_id=org_id,
        user_id=current_user.user_id,
        obligations=[_obligation_to_row(o) for o in all_obligations],
    )

    cascade = detect_cascade(profile)
    bc = build_business_case(result, cascade)
    return EvaluationResponse(
        ruleset_version=result.ruleset_version,
        applicable=[_obligation_to_dto(o) for o in result.applicable],
        uncertain=[_obligation_to_dto(o) for o in result.uncertain],
        not_applicable=[_obligation_to_dto(o) for o in result.not_applicable],
        timeline=[TimelineItemDTO(date=d, framework=f, what=w) for d, f, w in result.timeline],
        business_case=BusinessCaseDTO(
            headline=bc.headline,
            primary_driver=bc.primary_driver,
            applicable_count=bc.applicable_count,
            uncertain_count=bc.uncertain_count,
            at_stake=bc.at_stake,
            watch_items=bc.watch_items,
            cascade_exposure=bc.cascade_exposure,
        ),
        cascade=[
            CascadeSignalDTO(
                customer=c.customer,
                matched_buyer=c.matched_buyer,
                regimes=c.regimes,
                rationale=c.rationale,
            )
            for c in cascade
        ],
    )


@router.get("/scope-3/obligations", response_model=list[ObligationDTO])
def list_saved_obligations(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[ObligationDTO]:
    rows = store.list_obligations(
        access_token=current_user.access_token, org_id=_org_id(current_user)
    )
    return [_row_to_dto(r) for r in rows]


@router.post("/scope-3/obligations/sbti-readiness", response_model=SBTiReadinessResponse)
def sbti_readiness(
    body: SBTiReadinessRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> SBTiReadinessResponse:
    org_id = _org_id(current_user)
    profile = _load_profile(current_user, org_id)
    categories = inv_store.list_category_results(
        access_token=current_user.access_token, inventory_id=body.inventory_id
    )
    scope3_by_category = {
        int(c["scope3_category"]): float(c["total_kg_co2e"] or 0) for c in categories
    }
    r = assess_sbti_readiness(
        profile,
        scope3_by_category,
        covered_categories=set(body.covered_categories),
        version=body.version,
        horizon=body.horizon,
    )
    return SBTiReadinessResponse(
        category_class=r.category_class,
        scope3_target_mandatory=r.scope3_target_mandatory,
        base_year_assurance_required=r.base_year_assurance_required,
        version=r.version,
        horizon=r.horizon,
        total_scope3_kg=r.total_scope3_kg,
        required_categories=r.required_categories,
        covered_categories=r.covered_categories,
        coverage_gap=r.coverage_gap,
        meets_requirement=r.meets_requirement,
        notes=r.notes,
    )


# --- mapping helpers --------------------------------------------------------


def _obligation_to_row(o: Obligation) -> dict:
    return {
        "rule_id": o.rule_id,
        "framework": o.framework,
        "applies": o.applies,
        "reason": o.reason,
        "threshold_detail": o.threshold_detail,
        "confidence": o.confidence,
        "status": o.status,
        "due": [asdict(d) for d in o.due],
        "assurance": o.assurance,
        "citation": o.citation,
        "priority": o.priority,
        "ruleset_version": o.ruleset_version,
    }


def _obligation_to_dto(o: Obligation) -> ObligationDTO:
    return ObligationDTO(
        rule_id=o.rule_id,
        framework=o.framework,
        applies=o.applies,
        reason=o.reason,
        threshold_detail=o.threshold_detail,
        confidence=o.confidence,
        status=o.status,
        due=[DueItemDTO(what=d.what, date=d.date, note=d.note) for d in o.due],
        assurance=o.assurance,
        citation=o.citation,
        priority=o.priority,
    )


def _row_to_dto(r: dict) -> ObligationDTO:
    return ObligationDTO(
        rule_id=r["rule_id"],
        framework=r["framework"],
        applies=r["applies"],
        reason=r.get("reason") or "",
        threshold_detail=r.get("threshold_detail") or "",
        confidence=r.get("confidence") or "",
        status=r.get("status") or "",
        due=[DueItemDTO(**d) for d in (r.get("due") or [])],
        assurance=r.get("assurance"),
        citation=r.get("citation") or "",
        priority=int(r.get("priority") or 0),
    )
