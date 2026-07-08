"""Scope-3 use-phase routes (Epic H). Orchestrate only — Cat 11 calc + templates
live in s3_usephase; captured specs in db.s3_usephase_store. org_id resolved here.
Base path `/scope-3`. Ships dark. NOT yet run against a live DB.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

import db.s3_usephase_store as store
from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope3_schemas import UsePhaseCalcRequest, UsePhaseResultDTO
from db.org_store import get_active_org
from s3_usephase.calc import direct_use_phase, indirect_use_phase
from s3_usephase.models import ProductEnergySpec, UseProfile
from s3_usephase.templates import available_sub_sectors

router = APIRouter(tags=["scope3-usephase"])

_SPEC_FIELDS = (
    "product_ref",
    "energy_per_use_kwh",
    "water_l_per_use",
    "standby_power_w",
    "fuel_kwh_per_use",
    "uses_per_year",
    "lifetime_years",
    "units_sold",
    "region",
    "mode",
)


def _org_id(current_user: CurrentUser) -> str:
    org = get_active_org(current_user.access_token, user_id=current_user.user_id)
    if org is None:
        raise HTTPException(status_code=400, detail="No active organization for this user.")
    return org.id


def calc_from_request(body: UsePhaseCalcRequest) -> UsePhaseResultDTO:
    """Pure — compute a Cat 11 use-phase result from the request. Unit-testable."""
    spec = ProductEnergySpec(
        product_name=body.product_ref,
        energy_per_use_kwh=body.energy_per_use_kwh,
        water_l_per_use=body.water_l_per_use,
        standby_power_w=body.standby_power_w,
        fuel_kwh_per_use=body.fuel_kwh_per_use,
    )
    profile = UseProfile(uses_per_year=body.uses_per_year, lifetime_years=body.lifetime_years)
    if body.mode == "indirect":
        result = indirect_use_phase(spec, profile, body.units_sold, region=body.region)
    else:
        result = direct_use_phase(
            spec, profile, body.units_sold, region=body.region, include_standby=body.include_standby
        )
    return UsePhaseResultDTO(
        product_name=result.product_name,
        units_sold=result.units_sold,
        kg_co2e=result.kg_co2e,
        direct_or_indirect=result.direct_or_indirect,
        method=result.method,
        ef_source=result.ef_source,
        dq_note=result.dq_note,
        breakdown=result.breakdown,
    )


@router.get("/scope-3/use-phase/sub-sectors", response_model=list[str])
def sub_sectors() -> list[str]:
    return available_sub_sectors()


@router.post("/scope-3/use-phase/calc", response_model=UsePhaseResultDTO)
def calculate(
    body: UsePhaseCalcRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> UsePhaseResultDTO:
    return calc_from_request(body)


@router.post("/scope-3/use-phase/specs", response_model=dict)
def create_spec(
    body: UsePhaseCalcRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    return store.create_spec(
        access_token=current_user.access_token,
        org_id=_org_id(current_user),
        user_id=current_user.user_id,
        spec={k: getattr(body, k) for k in _SPEC_FIELDS},
    )


@router.get("/scope-3/use-phase/specs", response_model=list[dict])
def list_specs(current_user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return store.list_specs(access_token=current_user.access_token, org_id=_org_id(current_user))


@router.delete("/scope-3/use-phase/specs/{spec_id}", status_code=204)
def delete_spec(spec_id: int, current_user: CurrentUser = Depends(get_current_user)) -> None:
    store.delete_spec(access_token=current_user.access_token, spec_id=spec_id)
