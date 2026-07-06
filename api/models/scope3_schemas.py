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
