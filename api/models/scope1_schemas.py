"""Pydantic request/response models for the Scope 1 module (isolated).

Kept separate from api.models.schemas so the Scope 1 API surface does not couple
to the Carbon OS schemas. CRUD endpoints echo the stored row (a dict); computed
endpoints (consolidation, readiness, report, trace) use the models below.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# --- Org structure ----------------------------------------------------------

class CreateEntityRequest(BaseModel):
    name: str
    jurisdiction: str = Field(min_length=2, max_length=2)   # ISO 3166-1 alpha-2
    entity_type: str
    parent_entity_id: str | None = None
    equity_pct: float | None = None
    economic_interest_pct: float | None = None
    has_financial_control: bool = False
    has_operational_control: bool = False
    effective_from: str                                     # ISO date


class CreateFacilityRequest(BaseModel):
    entity_id: str
    name: str
    address: str | None = None
    city: str | None = None
    state_region: str | None = None
    country: str | None = Field(default=None, max_length=2)


class CreateDataOwnerRequest(BaseModel):
    name: str
    email: str | None = None
    role_title: str | None = None
    owner_type: str = "internal"


# --- Inventory + consolidation ----------------------------------------------

class CreateInventoryRequest(BaseModel):
    reporting_entity_id: str
    reporting_year: int
    period_start: str
    period_end: str
    consolidation_approach: str        # equity_share|financial_control|operational_control
    base_year: int
    significance_threshold_pct: float | None = None


class ConsolidationPreviewRequest(BaseModel):
    approach: str
    equity_pct: float | None = None
    economic_interest_pct: float | None = None
    has_financial_control: bool = False
    has_operational_control: bool = False
    entity_type: str | None = None


class ConsolidationPreviewResponse(BaseModel):
    multiplier: float
    rationale: str


class UpsertBoundaryRequest(BaseModel):
    inventory_id: str
    entity_id: str
    in_scope: bool = True
    exclusion_reason: str | None = None


# --- Sources ----------------------------------------------------------------

class CreateSourceRequest(BaseModel):
    entity_id: str
    facility_id: str | None = None
    source_name: str
    source_category: str               # stationary_combustion|mobile_combustion|...
    source_subcategory: str | None = None
    primary_fuel: str | None = None
    vehicle_class: str | None = None
    vehicle_model_year: int | None = None


class ExcludeSourceRequest(BaseModel):
    rationale: str


# --- Member roles -----------------------------------------------------------

class SetRoleRequest(BaseModel):
    role: str                              # admin | editor | viewer


class InviteMemberRequest(BaseModel):
    email: str
    role: str = "editor"                   # admin | editor | viewer


# --- Data-collection orchestration ------------------------------------------

class AssignOwnerRequest(BaseModel):
    data_owner_id: str


class CollectionStatusRequest(BaseModel):
    inventory_id: str
    emission_source_id: str
    period_start: str
    period_end: str
    status: str                        # missing|requested|in_progress|received|entered|verified
    data_owner_id: str | None = None
    notes: str | None = None


# --- OCR review queue -------------------------------------------------------

class OcrReviewRequest(BaseModel):
    action: str                            # approve | reject
    corrected_fields: dict[str, str] | None = None
    # Required for approve — the reviewed fields become an emission record:
    emission_source_id: str | None = None
    fuel_or_activity: str | None = None
    activity_value: float | None = None
    activity_unit: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    data_quality_tier: int = 3             # OCR + human review = Tier 3 (research/2.3 B4)


# --- Intake (records) -------------------------------------------------------

class StationaryRecordRequest(BaseModel):
    inventory_id: str
    emission_source_id: str
    period_start: str
    period_end: str
    fuel_or_activity: str
    activity_value: float
    activity_unit: str
    biogenic: bool = False
    hhv_override: float | None = None
    data_quality_tier: int = 4
    activity_data_source: str = "manual"
    evidence_document_id: str | None = None


class MobileRecordRequest(BaseModel):
    inventory_id: str
    emission_source_id: str
    period_start: str
    period_end: str
    fuel_or_activity: str
    fuel_quantity: float
    fuel_unit: str
    miles: float | None = None
    model_year: int | None = None
    distance_activity: str | None = None
    data_quality_tier: int = 4
    activity_data_source: str = "manual"
    evidence_document_id: str | None = None


# --- Readiness + report -----------------------------------------------------

class ReadinessResponse(BaseModel):
    total: int
    complete: int
    completeness_pct: float
    by_status: dict[str, int]
    items: list[dict]


class GasBreakdownDTO(BaseModel):
    co2_fossil_tco2e: float
    ch4_tco2e: float
    n2o_tco2e: float
    sf6_tco2e: float
    nf3_tco2e: float
    total_tco2e: float


class FacilityBreakdownDTO(BaseModel):
    facility_id: str | None
    facility_name: str | None
    tco2e: float


class InventoryReportResponse(BaseModel):
    ar_version: str
    total_scope1_tco2e: float
    biogenic_co2_tco2e: float
    by_gas: GasBreakdownDTO
    by_facility: list[FacilityBreakdownDTO]
    record_count: int
