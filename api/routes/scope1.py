"""FastAPI routes for the Scope 1 module (isolated under /api/scope1).

Thin orchestration: validate -> call business logic (s1_calc / s1_consolidation /
s1_reporting) -> persist via db.scope1_store (RLS-scoped). No calculations inline.
"""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query

from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope1_schemas import (
    ConsolidationPreviewRequest,
    ConsolidationPreviewResponse,
    CreateDataOwnerRequest,
    CreateEntityRequest,
    CreateFacilityRequest,
    CreateInventoryRequest,
    CreateSourceRequest,
    ExcludeSourceRequest,
    FacilityBreakdownDTO,
    GasBreakdownDTO,
    InventoryReportResponse,
    MobileRecordRequest,
    ReadinessResponse,
    StationaryRecordRequest,
    UpsertBoundaryRequest,
)
from db import scope1_store as store
from db.scope1_store import NoActiveOrgError
from s1_calc import GasMasses, calculate_mobile, calculate_stationary
from s1_consolidation import compute_consolidation_multiplier
from s1_factors import EmissionFactorLibrary, MissingEmissionFactor
from s1_reporting import ReportRecord, build_inventory_report, trace_record

router = APIRouter(prefix="/api/scope1", tags=["scope1"])

_COMPLETE_STATUSES = {"received", "entered", "verified"}


def _library() -> EmissionFactorLibrary:
    """Canonical EPA library (mirrors the seeded s1_ef_record reference data)."""
    return EmissionFactorLibrary.default()


def _guard(func, *args, **kwargs):
    """Run a store call, mapping the no-active-org case to a 400."""
    try:
        return func(*args, **kwargs)
    except NoActiveOrgError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- Entities / facilities / data owners ------------------------------------

@router.post("/entities")
def create_entity(req: CreateEntityRequest, user: CurrentUser = Depends(get_current_user)) -> dict:
    return _guard(store.create_entity, req.model_dump(exclude_none=True),
                  access_token=user.access_token, user_id=user.user_id)


@router.get("/entities")
def list_entities(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return _guard(store.list_entities, access_token=user.access_token, user_id=user.user_id)


@router.post("/facilities")
def create_facility(req: CreateFacilityRequest, user: CurrentUser = Depends(get_current_user)) -> dict:
    return _guard(store.create_facility, req.model_dump(exclude_none=True),
                  access_token=user.access_token, user_id=user.user_id)


@router.get("/facilities")
def list_facilities(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return _guard(store.list_facilities, access_token=user.access_token, user_id=user.user_id)


@router.post("/data-owners")
def create_data_owner(req: CreateDataOwnerRequest, user: CurrentUser = Depends(get_current_user)) -> dict:
    return _guard(store.create_data_owner, req.model_dump(exclude_none=True),
                  access_token=user.access_token, user_id=user.user_id)


# --- Inventory + consolidation ----------------------------------------------

@router.post("/inventories")
def create_inventory(req: CreateInventoryRequest, user: CurrentUser = Depends(get_current_user)) -> dict:
    return _guard(store.create_inventory, req.model_dump(exclude_none=True),
                  access_token=user.access_token, user_id=user.user_id)


@router.get("/inventories")
def list_inventories(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return _guard(store.list_inventories, access_token=user.access_token, user_id=user.user_id)


@router.post("/inventories/{inventory_id}/lock")
def lock_inventory(inventory_id: str, user: CurrentUser = Depends(get_current_user)) -> dict:
    return _guard(store.lock_inventory, inventory_id,
                  access_token=user.access_token, user_id=user.user_id)


@router.post("/consolidation/preview", response_model=ConsolidationPreviewResponse)
def consolidation_preview(req: ConsolidationPreviewRequest) -> ConsolidationPreviewResponse:
    """Pure preview of the consolidation multiplier — no persistence."""
    try:
        result = compute_consolidation_multiplier(
            req.approach,
            equity_pct=req.equity_pct,
            economic_interest_pct=req.economic_interest_pct,
            has_financial_control=req.has_financial_control,
            has_operational_control=req.has_operational_control,
            entity_type=req.entity_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ConsolidationPreviewResponse(multiplier=result.multiplier, rationale=result.rationale)


@router.post("/boundary")
def upsert_boundary(req: UpsertBoundaryRequest, user: CurrentUser = Depends(get_current_user)) -> dict:
    """Compute the entity's multiplier from the inventory approach + control flags, then store it."""
    inv = _guard(store.get_inventory, req.inventory_id,
                 access_token=user.access_token, user_id=user.user_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Inventory not found.")
    entity = _guard(store.get_entity, req.entity_id,
                    access_token=user.access_token, user_id=user.user_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found.")

    result = compute_consolidation_multiplier(
        inv["consolidation_approach"],
        equity_pct=entity.get("equity_pct"),
        economic_interest_pct=entity.get("economic_interest_pct"),
        has_financial_control=entity.get("has_financial_control", False),
        has_operational_control=entity.get("has_operational_control", False),
        entity_type=entity.get("entity_type"),
    )
    row = {
        "inventory_id": req.inventory_id,
        "entity_id": req.entity_id,
        "in_scope": req.in_scope,
        "exclusion_reason": req.exclusion_reason,
        "applied_equity_pct": entity.get("economic_interest_pct") or entity.get("equity_pct"),
        "consolidation_multiplier": result.multiplier,
        "consolidation_rationale": result.rationale,
    }
    return _guard(store.upsert_boundary, row,
                  access_token=user.access_token, user_id=user.user_id)


# --- Sources ----------------------------------------------------------------

@router.post("/sources")
def create_source(req: CreateSourceRequest, user: CurrentUser = Depends(get_current_user)) -> dict:
    return _guard(store.create_source, req.model_dump(exclude_none=True),
                  access_token=user.access_token, user_id=user.user_id)


@router.get("/sources")
def list_sources(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return _guard(store.list_sources, access_token=user.access_token, user_id=user.user_id)


@router.post("/sources/{source_id}/exclude")
def exclude_source(source_id: str, req: ExcludeSourceRequest,
                   user: CurrentUser = Depends(get_current_user)) -> dict:
    return _guard(store.exclude_source, source_id, req.rationale,
                  access_token=user.access_token, user_id=user.user_id)


# --- Intake (records) -------------------------------------------------------

@router.post("/records/stationary")
def create_stationary_record(req: StationaryRecordRequest,
                             user: CurrentUser = Depends(get_current_user)) -> dict:
    try:
        result = calculate_stationary(
            req.fuel_or_activity, req.activity_value, req.activity_unit, _library(),
            biogenic=req.biogenic, hhv_override=req.hhv_override,
            data_quality_tier=req.data_quality_tier,
        )
    except MissingEmissionFactor as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    row = _record_row(req, result, req.activity_value, req.activity_unit)
    return _guard(store.create_record, row,
                  access_token=user.access_token, user_id=user.user_id)


@router.post("/records/mobile")
def create_mobile_record(req: MobileRecordRequest,
                         user: CurrentUser = Depends(get_current_user)) -> dict:
    try:
        result = calculate_mobile(
            req.fuel_or_activity, req.fuel_quantity, req.fuel_unit, _library(),
            miles=req.miles, model_year=req.model_year,
            distance_activity=req.distance_activity, data_quality_tier=req.data_quality_tier,
        )
    except MissingEmissionFactor as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    row = _record_row(req, result, req.fuel_quantity, req.fuel_unit)
    return _guard(store.create_record, row,
                  access_token=user.access_token, user_id=user.user_id)


# --- Readiness meter --------------------------------------------------------

@router.get("/inventories/{inventory_id}/readiness", response_model=ReadinessResponse)
def readiness(inventory_id: str, user: CurrentUser = Depends(get_current_user)) -> ReadinessResponse:
    statuses = _guard(store.list_collection_status, inventory_id,
                      access_token=user.access_token, user_id=user.user_id)
    total = len(statuses)
    complete = sum(1 for s in statuses if s.get("status") in _COMPLETE_STATUSES)
    by_status = Counter(s.get("status", "missing") for s in statuses)
    return ReadinessResponse(
        total=total,
        complete=complete,
        completeness_pct=(complete / total * 100.0) if total else 0.0,
        by_status=dict(by_status),
        items=statuses,
    )


# --- Reporting --------------------------------------------------------------

@router.get("/inventories/{inventory_id}/report", response_model=InventoryReportResponse)
def inventory_report(
    inventory_id: str,
    ar_version: str = Query("AR5"),
    user: CurrentUser = Depends(get_current_user),
) -> InventoryReportResponse:
    records = _guard(store.list_records_for_inventory, inventory_id,
                     access_token=user.access_token, user_id=user.user_id)
    sources = {s["id"]: s for s in _guard(
        store.list_sources, access_token=user.access_token, user_id=user.user_id)}
    facilities = {f["id"]: f["name"] for f in _guard(
        store.list_facilities, access_token=user.access_token, user_id=user.user_id)}
    boundaries = {b["entity_id"]: float(b["consolidation_multiplier"]) for b in _guard(
        store.list_boundaries, inventory_id,
        access_token=user.access_token, user_id=user.user_id)}

    report_records = [
        _report_record(rec, sources, facilities, boundaries) for rec in records
    ]
    try:
        report = build_inventory_report(report_records, ar_version)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return InventoryReportResponse(
        ar_version=report.ar_version,
        total_scope1_tco2e=report.total_scope1_tco2e,
        biogenic_co2_tco2e=report.biogenic_co2_tco2e,
        by_gas=GasBreakdownDTO(
            co2_fossil_tco2e=report.by_gas.co2_fossil_tco2e,
            ch4_tco2e=report.by_gas.ch4_tco2e,
            n2o_tco2e=report.by_gas.n2o_tco2e,
            sf6_tco2e=report.by_gas.sf6_tco2e,
            nf3_tco2e=report.by_gas.nf3_tco2e,
            total_tco2e=report.by_gas.total_tco2e,
        ),
        by_facility=[
            FacilityBreakdownDTO(facility_id=f.facility_id, facility_name=f.facility_name, tco2e=f.tco2e)
            for f in report.by_facility
        ],
        record_count=report.record_count,
    )


@router.get("/records/{record_id}/trace")
def record_trace(
    record_id: str,
    ar_version: str = Query("AR5"),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """View Source: the activity x EF x GWP chain behind a record's number."""
    rec = _guard(store.get_record, record_id,
                 access_token=user.access_token, user_id=user.user_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Record not found.")
    sources = {s["id"]: s for s in _guard(
        store.list_sources, access_token=user.access_token, user_id=user.user_id)}
    facilities = {f["id"]: f["name"] for f in _guard(
        store.list_facilities, access_token=user.access_token, user_id=user.user_id)}
    boundaries = {b["entity_id"]: float(b["consolidation_multiplier"]) for b in _guard(
        store.list_boundaries, rec["inventory_id"],
        access_token=user.access_token, user_id=user.user_id)}

    report_record = _report_record(rec, sources, facilities, boundaries)
    trace = trace_record(report_record, ar_version)
    trace["ef_source"] = rec.get("ef_source")
    trace["ef_tier"] = rec.get("ef_tier")
    trace["evidence_document_id"] = rec.get("evidence_document_id")
    return trace


# --- Internal helpers -------------------------------------------------------

def _record_row(req, result, activity_value: float, activity_unit: str) -> dict:
    gm = result.gas_masses
    co2_ref = next((r for r in result.ef_refs if r.gas == "CO2"), result.ef_refs[0])
    return {
        "inventory_id": req.inventory_id,
        "emission_source_id": req.emission_source_id,
        "period_start": req.period_start,
        "period_end": req.period_end,
        "activity_data_value": activity_value,
        "activity_data_unit": activity_unit,
        "activity_data_source": req.activity_data_source,
        "calculation_method": result.calculation_method,
        "heat_input_mmbtu": result.heat_input_mmbtu,
        "ef_source": f"{co2_ref.source} ({co2_ref.source_version})",
        "ef_tier": "T2" if result.calculation_method == "EF_Tier2" else "T1",
        "ef_selection_rank": co2_ref.selection_rank,
        "kg_co2_fossil": gm.kg_co2_fossil,
        "kg_co2_biogenic": gm.kg_co2_biogenic,
        "kg_ch4": gm.kg_ch4,
        "kg_n2o": gm.kg_n2o,
        "biogenic_fossil_tag": result.biogenic_fossil_tag,
        "data_quality_tier": result.data_quality_tier,
        "evidence_document_id": req.evidence_document_id,
    }


def _gas_masses(row: dict) -> GasMasses:
    return GasMasses(
        kg_co2_fossil=float(row.get("kg_co2_fossil") or 0.0),
        kg_co2_biogenic=float(row.get("kg_co2_biogenic") or 0.0),
        kg_ch4=float(row.get("kg_ch4") or 0.0),
        kg_n2o=float(row.get("kg_n2o") or 0.0),
        kg_sf6=float(row.get("kg_sf6") or 0.0),
        kg_nf3=float(row.get("kg_nf3") or 0.0),
    )


def _report_record(rec: dict, sources: dict, facilities: dict, boundaries: dict) -> ReportRecord:
    source = sources.get(rec["emission_source_id"], {})
    entity_id = source.get("entity_id")
    facility_id = source.get("facility_id")
    return ReportRecord(
        record_id=rec["id"],
        gas_masses=_gas_masses(rec),
        multiplier=boundaries.get(entity_id, 1.0),   # default 1.0 if no boundary set
        facility_id=facility_id,
        facility_name=facilities.get(facility_id),
        source_id=rec["emission_source_id"],
        source_name=source.get("source_name"),
    )
