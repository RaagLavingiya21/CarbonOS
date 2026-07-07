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

class SetBaseYearRequest(BaseModel):
    base_year: int
    base_year_total_tco2e: float
    base_year_gwp_version: str = "AR5"       # AR4|AR5|AR6
    evidence_document_id: str | None = None


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


# --- Process emissions -------------------------------------------------------

class CreateProcessRequest(BaseModel):
    inventory_id: str
    process_type: str                       # library key or "custom"
    gas_species: str = Field(pattern="^(Carbon dioxide|Methane|Nitrous oxide)$")
    activity_quantity: float = Field(ge=0)
    ef_value: float = Field(ge=0)
    activity_unit: str | None = None
    ef_unit: str | None = None
    ef_source: str | None = None
    facility_id: str | None = None
    description: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    data_quality_tier: int = 4
    evidence_document_id: str | None = None


class ProcessRecordDTO(BaseModel):
    id: str
    process_type: str
    gas_species: str
    facility_id: str | None = None
    activity_quantity: float
    activity_unit: str | None = None
    ef_value: float
    ef_unit: str | None = None
    emission_kg: float
    tco2e: float
    description: str | None = None
    data_quality_tier: int | None = None
    evidence_document_id: str | None = None


class ProcessReportResponse(BaseModel):
    ar_version: str
    records: list[ProcessRecordDTO]
    total_tco2e: float


# --- Fugitive (refrigerant) emissions ---------------------------------------

class CreateFugitiveRequest(BaseModel):
    inventory_id: str
    refrigerant: str
    method: str = Field(pattern="^(screening|material_balance)$")
    facility_id: str | None = None
    # Screening inputs:
    charge_kg: float | None = Field(default=None, ge=0)
    leak_rate_pct: float | None = Field(default=None, ge=0)
    # Material-balance inputs:
    purchases_kg: float | None = Field(default=None, ge=0)
    beginning_inventory_kg: float | None = Field(default=None, ge=0)
    ending_inventory_kg: float | None = Field(default=None, ge=0)
    description: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    data_quality_tier: int = 4
    evidence_document_id: str | None = None


class FugitiveRecordDTO(BaseModel):
    id: str
    refrigerant: str
    method: str
    facility_id: str | None = None
    leaked_kg: float
    gwp: float
    tco2e: float
    description: str | None = None
    data_quality_tier: int | None = None
    evidence_document_id: str | None = None


class FugitiveReportResponse(BaseModel):
    ar_version: str
    records: list[FugitiveRecordDTO]
    total_tco2e: float


# --- Base-year recalculation ------------------------------------------------

class CreateRecalcEventRequest(BaseModel):
    trigger_type: str = Field(
        pattern="^(acquisition|divestiture|outsourcing|insourcing|"
                "methodology_change|error_correction|organic_growth|organic_decline)$"
    )
    delta_tco2e: float
    description: str | None = None
    effective_date: str | None = None


class RecalcEventDTO(BaseModel):
    id: str
    trigger_type: str
    description: str | None = None
    delta_tco2e: float
    applied: bool
    effective_date: str | None = None
    is_structural: bool


class RecalcAnalysisResponse(BaseModel):
    inventory_id: str
    base_year: int | None = None
    base_year_total_tco2e: float
    significance_threshold_pct: float | None = None
    events: list[RecalcEventDTO]
    structural_delta_pending: float
    organic_delta: float
    restated_total: float
    pct_impact: float | None = None
    recalc_required: bool | None = None
    has_pending: bool


# --- Trends & emissions intensity -------------------------------------------

class SetInventoryMetricsRequest(BaseModel):
    annual_revenue: float | None = Field(default=None, ge=0)
    revenue_currency: str | None = None
    output_quantity: float | None = Field(default=None, ge=0)
    output_unit: str | None = None
    headcount: int | None = Field(default=None, ge=0)


class TrendPointDTO(BaseModel):
    inventory_id: str
    reporting_year: int
    total_tco2e: float
    is_base_year: bool
    yoy_abs: float | None = None
    yoy_pct: float | None = None
    per_revenue_mm: float | None = None
    revenue_currency: str = "USD"
    per_output: float | None = None
    output_unit: str | None = None
    per_headcount: float | None = None


class TrendsResponse(BaseModel):
    ar_version: str
    points: list[TrendPointDTO]
    base_year: int | None = None
    base_year_total_tco2e: float | None = None
    latest_vs_base_abs: float | None = None
    latest_vs_base_pct: float | None = None


# --- Emission factors (admin overrides) -------------------------------------

class EfFactorDTO(BaseModel):
    fuel_or_activity: str
    source_category: str
    gas: str
    value: float
    unit: str
    source: str
    source_version: str
    region: str = "US"
    biogenic: bool = False
    model_year: int | None = None
    is_override: bool = False
    basis: str | None = None
    override_id: str | None = None


class FactorsResponse(BaseModel):
    your_role: str
    factors: list[EfFactorDTO]
    override_count: int


class CreateEfOverrideRequest(BaseModel):
    fuel_or_activity: str
    source_category: str
    gas: str = Field(pattern="^(CO2|CH4|N2O)$")
    value: float = Field(gt=0)
    unit: str
    source: str
    source_version: str
    region: str = "US"
    hhv: float | None = None
    hhv_unit: str | None = None
    tier: int | None = None
    biogenic: bool = False
    model_year: int | None = None
    basis: str = Field(default="custom", pattern="^(measured|supplier|custom)$")
    notes: str | None = None


# --- Onboarding wizard ------------------------------------------------------

class OnboardingStepDTO(BaseModel):
    key: str
    title: str
    description: str
    href: str
    cta: str
    done: bool
    count: int


class OnboardingResponse(BaseModel):
    steps: list[OnboardingStepDTO]
    complete: int
    total: int
    pct: float
    next_key: str | None = None
