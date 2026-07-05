"""Scope 2 calculation routes — run the dual-method engine and persist results.

Loads the org's active sites, active (non-superseded) bills, and the factor
library, runs the pure engine (s2_calc.engine), and writes an immutable
calculation snapshot plus its audit trail. Franchise sites are excluded from
Scope 2 (routed to Scope 3 Cat 14 elsewhere). Instruments (market-based EAC
coverage) arrive in M1; M0 market-based uses residual mix for all uncovered load.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope2_schemas import (
    CalculationDTO,
    RunCalculationRequest,
    RunCalculationResponse,
)
from api.routes.scope2_deps import resolve_org_id
from db import (
    s2_audit_store,
    s2_bill_store,
    s2_calc_store,
    s2_factor_store,
    s2_site_store,
)
from s2_calc.engine import compute_dual_method
from s2_calc.mappers import (
    consumption_from_bill_row,
    factor_from_row,
    site_profile_from_row,
)
from s2_factors.library import FactorLibrary, FactorNotFoundError

router = APIRouter(prefix="/api/scope2", tags=["scope2"])


@router.post("/calculations", response_model=RunCalculationResponse)
def run_calculation(
    request: RunCalculationRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> RunCalculationResponse:
    org_id = resolve_org_id(current_user)
    token = current_user.access_token

    site_rows = s2_site_store.list_sites(token)
    active = [
        row
        for row in site_rows
        if not row.get("franchise_flag")
        and (row.get("status") or "active") == "active"
    ]
    if not active:
        raise HTTPException(
            status_code=400, detail="No active, non-franchise sites to calculate."
        )

    sites = [site_profile_from_row(row) for row in active]
    consumption = [
        record
        for record in (
            consumption_from_bill_row(bill)
            for bill in s2_bill_store.list_active_bills(token)
        )
        if record is not None
    ]
    library = FactorLibrary(
        [factor_from_row(row) for row in s2_factor_store.load_factors(token)]
    )

    try:
        result = compute_dual_method(
            sites, consumption, [], library, request.reporting_year
        )
    except FactorNotFoundError as exc:
        raise HTTPException(status_code=422, detail=f"Missing emission factor: {exc}") from exc

    total_mwh = sum(sr.consumption_mwh for sr in result.site_results)
    fallback_count = sum(1 for sr in result.site_results if sr.market_fallback_flagged)
    factor_versions = {
        sr.site_id: sr.location_factor_vintage for sr in result.site_results
    }

    calc_id = s2_calc_store.save_calculation(
        {
            "reporting_year": result.reporting_year,
            "scope": "entity",
            "site_id": None,
            "location_based_kg_co2e": result.location_based_kg_co2e,
            "market_based_kg_co2e": result.market_based_kg_co2e,
            "consumption_mwh": total_mwh,
            "market_tier": None,
            "market_fallback_flagged": fallback_count > 0,
            "factor_versions": factor_versions,
            "methodology_notes": (
                "Dual-method (location + market-based) per GHG Protocol Scope 2."
            ),
        },
        org_id=org_id,
        user_id=current_user.user_id,
        access_token=token,
    )

    s2_audit_store.insert_calc_audit_entries(
        result.audit_entries,
        calc_id=calc_id,
        org_id=org_id,
        user_id=current_user.user_id,
        access_token=token,
    )

    return RunCalculationResponse(
        calc_id=calc_id,
        reporting_year=result.reporting_year,
        location_based_kg_co2e=result.location_based_kg_co2e,
        market_based_kg_co2e=result.market_based_kg_co2e,
        consumption_mwh=total_mwh,
        site_count=len(result.site_results),
        market_fallback_site_count=fallback_count,
    )


@router.get("/calculations", response_model=list[CalculationDTO])
def list_calculations(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[CalculationDTO]:
    rows = s2_calc_store.list_calculations(current_user.access_token)
    return [CalculationDTO.from_row(row) for row in rows]
