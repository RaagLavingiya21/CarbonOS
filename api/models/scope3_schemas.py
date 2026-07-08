"""Pydantic request/response DTOs for the Scope-3 module (hygiene: DTOs live in
api/models/scope3_schemas.py). Kept separate from the shared api/models/schemas
so the Scope-3 lane owns its own contract.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateInventoryRequest(BaseModel):
    reporting_year: int
    boundary_approach: str = "operational_control"


class InventoryVersionDTO(BaseModel):
    inventory_id: int
    org_id: str
    reporting_year: int
    boundary_approach: str
    status: str
    is_base_year: bool
    total_kg_co2e: float | None = None
    version: int
    created_at: str | None = None
    locked_at: str | None = None


class SpendImportResponse(BaseModel):
    inventory_id: int
    parsed_rows: int
    flagged_rows: int
    file_errors: list[str] = Field(default_factory=list)


class ClassifyResponse(BaseModel):
    inventory_id: int
    classified: int
    flagged_for_review: int


class CategoryResultDTO(BaseModel):
    scope3_category: int
    method: str
    total_kg_co2e: float
    line_count: int
    notes: str | None = None


class InventoryDetailDTO(BaseModel):
    version: InventoryVersionDTO
    categories: list[CategoryResultDTO] = Field(default_factory=list)


# --- Epic C: obligation front door ------------------------------------------


class CompanyProfileRequest(BaseModel):
    annual_revenue_usd: float | None = None
    employee_count: int | None = None
    is_us_entity: bool = False
    does_business_in_ca: bool = False
    eu_turnover_eur: float | None = None
    eu_subsidiary: bool = False
    eu_branch_turnover_eur: float | None = None
    listed_jurisdictions: list[str] = Field(default_factory=list)
    sector: str = ""
    is_flag_sector: bool = False
    key_customers: list[str] = Field(default_factory=list)


class DueItemDTO(BaseModel):
    what: str
    date: str | None = None
    note: str | None = None


class ObligationDTO(BaseModel):
    rule_id: str
    framework: str
    applies: str
    reason: str
    threshold_detail: str
    confidence: str
    status: str
    due: list[DueItemDTO] = Field(default_factory=list)
    assurance: str | None = None
    citation: str
    priority: int


class TimelineItemDTO(BaseModel):
    date: str
    framework: str
    what: str


class CascadeSignalDTO(BaseModel):
    customer: str
    matched_buyer: str
    regimes: list[str] = Field(default_factory=list)
    rationale: str


class BusinessCaseDTO(BaseModel):
    headline: str
    primary_driver: str | None = None
    applicable_count: int
    uncertain_count: int
    at_stake: list[str] = Field(default_factory=list)
    watch_items: list[str] = Field(default_factory=list)
    cascade_exposure: list[str] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    ruleset_version: str
    applicable: list[ObligationDTO] = Field(default_factory=list)
    uncertain: list[ObligationDTO] = Field(default_factory=list)
    not_applicable: list[ObligationDTO] = Field(default_factory=list)
    timeline: list[TimelineItemDTO] = Field(default_factory=list)
    business_case: BusinessCaseDTO
    cascade: list[CascadeSignalDTO] = Field(default_factory=list)


class SBTiReadinessRequest(BaseModel):
    inventory_id: int
    version: str = "v2.0"
    horizon: str = "near_term"
    covered_categories: list[int] = Field(default_factory=list)


class SBTiReadinessResponse(BaseModel):
    category_class: str
    scope3_target_mandatory: bool
    base_year_assurance_required: bool
    version: str
    horizon: str
    total_scope3_kg: float
    required_categories: list[int] = Field(default_factory=list)
    covered_categories: list[int] = Field(default_factory=list)
    coverage_gap: list[int] = Field(default_factory=list)
    meets_requirement: bool | None = None
    notes: list[str] = Field(default_factory=list)


# --- Epic B: questionnaire answer -------------------------------------------


class QuestionnaireCreateRequest(BaseModel):
    customer_name: str | None = None
    framework: str | None = None
    deadline: str | None = None
    inventory_id: int | None = None


class QuestionnaireRequestDTO(BaseModel):
    request_id: int
    org_id: str
    customer_name: str | None = None
    framework: str
    status: str
    deadline: str | None = None
    inventory_id: int | None = None
    created_at: str | None = None


class DetectResponse(BaseModel):
    request_id: int
    framework: str
    is_low_confidence: bool
    question_count: int


class MapResponse(BaseModel):
    request_id: int
    mapped: int
    needs_human: int


class QuestionDTO(BaseModel):
    question_id: int
    question_index: int
    question_text: str
    question_type: str
    framework_field_key: str | None = None


class QuestionMappingDTO(BaseModel):
    question_id: int
    datapoint_ref: str | None = None
    mapped_value: float | None = None
    answer_text: str | None = None
    confidence_score: float
    method: str
    citation: str | None = None
    flag_status: str


class QuestionnaireDetailDTO(BaseModel):
    request: QuestionnaireRequestDTO
    questions: list[QuestionDTO] = Field(default_factory=list)
    mappings: list[QuestionMappingDTO] = Field(default_factory=list)


# --- Epic D: SBTi / FLAG targets --------------------------------------------


class TargetWizardRequest(BaseModel):
    inventory_id: int
    base_year: int
    target_year: int
    reduction_pct: float
    method: str = "absolute"
    horizon: str = "near_term"
    version: str = "v2.0"
    covered_categories: list[int] = Field(default_factory=list)
    sector: str = ""
    flag_kg_co2e: float = 0.0


class TrajectoryPointDTO(BaseModel):
    year: int
    target_kg_co2e: float


class AmbitionDTO(BaseModel):
    chosen_reduction_pct: float
    reference_reduction_pct: float
    meets_reference: bool
    note: str


class FlagDTO(BaseModel):
    is_flag_required: bool
    flag_share: float
    reason: str
    no_deforestation_commitment_date: str | None = None


class DraftTargetDTO(BaseModel):
    version: str
    horizon: str
    category_class: str
    scope3_target_mandatory: bool
    base_year_assurance_required: bool
    total_scope3_kg: float
    required_categories: list[int] = Field(default_factory=list)
    coverage_gap: list[int] = Field(default_factory=list)
    meets_requirement: bool | None = None
    trajectory: list[TrajectoryPointDTO] = Field(default_factory=list)
    ambition: AmbitionDTO
    flag: FlagDTO | None = None
    notes: list[str] = Field(default_factory=list)


class TargetDTO(BaseModel):
    target_id: int
    org_id: str
    type: str
    method: str
    sbti_version: str
    base_year: int | None = None
    target_year: int | None = None
    reduction_pct: float | None = None
    inventory_base_id: int | None = None
    status: str
    assurance_required: bool


# --- Epic G: disclosure -----------------------------------------------------


class DisclosureCalcRequest(BaseModel):
    inventory_id: int
    framework: str  # esrs_e1 | sb253 | ifrs_s2


class DisclosureDatapointDTO(BaseModel):
    key: str
    label: str
    value: float | None = None
    text: str | None = None
    unit: str
    source_ref: str | None = None
    flag: str


class DisclosureResultDTO(BaseModel):
    framework: str
    format_version: str
    is_provisional: bool
    datapoints: list[DisclosureDatapointDTO] = Field(default_factory=list)
    category_breakdown: list[DisclosureDatapointDTO] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# --- Epic E: progress -------------------------------------------------------


class ProgressTrackRequest(BaseModel):
    base_inventory_id: int
    current_inventory_id: int
    target_id: int | None = None
    # {reporting_year: target_kg_co2e}; JSON object keys are strings.
    trajectory: dict[str, float] = Field(default_factory=dict)


class ProgressResultDTO(BaseModel):
    current_year: int
    base_total_kg: float
    real_total_kg: float
    actual_total_kg: float
    trajectory_target_kg: float | None = None
    on_track: bool | None = None
    method_delta_kg: float
    notes: list[str] = Field(default_factory=list)


class RecalcRequest(BaseModel):
    trigger: str
    significance_pct: float
    threshold_pct: float | None = None


class RecalcResultDTO(BaseModel):
    trigger: str
    significance_pct: float
    threshold_pct: float
    recalc_required: bool
    rationale: str
