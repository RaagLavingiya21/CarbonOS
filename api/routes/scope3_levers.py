"""Scope-3 levers / MAC / claims routes (Epic I). Orchestrate only — lever
library, MAC curve and green-claims logic live in s3_levers; claim assessments
persist in db.s3_claims_store. org_id resolved here. Base path `/scope-3`.
Ships dark. Claims are legal-sensitive (flag exposure, not legal advice).
NOT yet run against a live DB.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query

import db.s3_claims_store as store
from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope3_schemas import (
    ClaimAssessmentDTO,
    ClaimAssessRequest,
    ComplianceFlagDTO,
    LeverDTO,
    MacPointDTO,
    MacRequest,
)
from db.org_store import get_active_org
from s3_levers.claims import assess_claim
from s3_levers.library import match_levers
from s3_levers.mac import build_mac_curve
from s3_levers.models import Lever

router = APIRouter(tags=["scope3-levers"])


def _org_id(current_user: CurrentUser) -> str:
    org = get_active_org(current_user.access_token, user_id=current_user.user_id)
    if org is None:
        raise HTTPException(status_code=400, detail="No active organization for this user.")
    return org.id


def _lever_dto(lev: Lever) -> LeverDTO:
    return LeverDTO(
        lever_id=lev.lever_id,
        name=lev.name,
        category=lev.category,
        abatement_pct=lev.abatement_pct,
        cost_per_tco2e=lev.cost_per_tco2e,
        applicability=lev.applicability,
        source=lev.source,
    )


@router.get("/scope-3/levers", response_model=list[LeverDTO])
def levers(
    categories: str = Query(..., description="Comma-separated Scope 3 categories, e.g. 1,4,11"),
    sub_sector: str | None = Query(None),
    _current_user: CurrentUser = Depends(get_current_user),
) -> list[LeverDTO]:
    cats = {int(c) for c in categories.split(",") if c.strip().isdigit()}
    return [_lever_dto(lev) for lev in match_levers(cats, sub_sector)]


@router.post("/scope-3/mac", response_model=list[MacPointDTO])
def mac(
    body: MacRequest,
    _current_user: CurrentUser = Depends(get_current_user),
) -> list[MacPointDTO]:
    totals = {int(k): v for k, v in body.category_totals_tco2e.items()}
    levers = match_levers(set(totals), body.sub_sector)
    points = build_mac_curve(levers, totals)
    return [MacPointDTO(**asdict(p)) for p in points]


@router.post("/scope-3/claims/assess", response_model=ClaimAssessmentDTO)
def assess(
    body: ClaimAssessRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ClaimAssessmentDTO:
    result = assess_claim(
        body.claim_text,
        primary_data_share=body.primary_data_share,
        assured=body.assured,
        jurisdiction=body.jurisdiction,
        offset_based=body.offset_based,
    )
    flags = [asdict(f) for f in result.flags]
    store.save_claim(
        access_token=current_user.access_token,
        org_id=_org_id(current_user),
        user_id=current_user.user_id,
        fields={
            "claim_text": result.claim_text,
            "jurisdiction": result.jurisdiction,
            "substantiable": result.substantiable,
            "substantiation_reason": result.substantiation_reason,
            "ruleset_version": result.ruleset_version,
            "flags": flags,
        },
    )
    return ClaimAssessmentDTO(
        claim_text=result.claim_text,
        jurisdiction=result.jurisdiction,
        substantiable=result.substantiable,
        substantiation_reason=result.substantiation_reason,
        ruleset_version=result.ruleset_version,
        flags=[ComplianceFlagDTO(**f) for f in flags],
    )


@router.get("/scope-3/claims", response_model=list[dict])
def list_claims(current_user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return store.list_claims(access_token=current_user.access_token, org_id=_org_id(current_user))
