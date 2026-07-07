"""Pydantic request/response models for the Scope 2 ("Grid") API layer.

Kept separate from api/models/schemas.py so the Scope 2 module shares no domain
types with the Carbon OS (Scope 3 / PACT) product. Only infra types (auth, health)
are shared at the app level.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, field_validator

from s2_sites.geomap import EGRID_SUBREGIONS, is_valid_subregion
from s2_sites.templates import SITE_TEMPLATES, SiteTemplate


class Scope2HealthResponse(BaseModel):
    status: str
    module: str = "scope2"


class SiteTemplateDTO(BaseModel):
    site_type: str
    label: str
    energy_carriers: list[str]
    default_ownership: str
    default_lease_type: str
    notes: str
    typical_utilities: list[str]

    @classmethod
    def from_domain(cls, template: SiteTemplate) -> "SiteTemplateDTO":
        return cls(
            site_type=template.site_type,
            label=template.label,
            energy_carriers=list(template.energy_carriers),
            default_ownership=template.default_ownership,
            default_lease_type=template.default_lease_type,
            notes=template.notes,
            typical_utilities=list(template.typical_utilities),
        )


def all_site_template_dtos() -> list[SiteTemplateDTO]:
    return [SiteTemplateDTO.from_domain(t) for t in SITE_TEMPLATES.values()]


# --- Sites ------------------------------------------------------------------


class CreateSiteRequest(BaseModel):
    name: str
    site_type: str
    address: str | None = None
    zip: str | None = None
    country: str = "US"
    egrid_subregion: str | None = None
    iea_country: str | None = None
    ownership: str | None = None
    lease_type: str | None = None
    franchise_flag: bool = False
    consolidation_approach: str = "operational_control"
    status: str = "active"

    @field_validator("egrid_subregion")
    @classmethod
    def _validate_subregion(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        code = value.strip().upper()
        if not is_valid_subregion(code):
            raise ValueError(
                f"Unknown eGRID subregion '{value}'. Must be one of {sorted(EGRID_SUBREGIONS)}."
            )
        return code


class EgridSubregionDTO(BaseModel):
    code: str
    name: str


def all_egrid_subregion_dtos() -> list[EgridSubregionDTO]:
    return [
        EgridSubregionDTO(code=code, name=name)
        for code, name in EGRID_SUBREGIONS.items()
    ]


class UpdateSiteRequest(BaseModel):
    name: str | None = None
    address: str | None = None
    zip: str | None = None
    egrid_subregion: str | None = None
    iea_country: str | None = None
    ownership: str | None = None
    lease_type: str | None = None
    franchise_flag: bool | None = None
    status: str | None = None


class SiteDTO(BaseModel):
    site_id: int
    name: str
    site_type: str
    address: str | None = None
    zip: str | None = None
    country: str | None = None
    egrid_subregion: str | None = None
    iea_country: str | None = None
    ownership: str | None = None
    lease_type: str | None = None
    franchise_flag: bool = False
    consolidation_approach: str | None = None
    status: str | None = None

    @classmethod
    def from_row(cls, row: dict) -> "SiteDTO":
        return cls(
            site_id=int(row["site_id"]),
            name=row["name"],
            site_type=row["site_type"],
            address=row.get("address"),
            zip=row.get("zip"),
            country=row.get("country"),
            egrid_subregion=row.get("egrid_subregion"),
            iea_country=row.get("iea_country"),
            ownership=row.get("ownership"),
            lease_type=row.get("lease_type"),
            franchise_flag=bool(row.get("franchise_flag", False)),
            consolidation_approach=row.get("consolidation_approach"),
            status=row.get("status"),
        )


# --- CSV import (preview) ---------------------------------------------------


class CsvImportRequest(BaseModel):
    csv_text: str
    mapping: dict[str, str]  # canonical field -> source column header


class CsvBillPreviewDTO(BaseModel):
    site_ref: str
    period_start: str
    period_end: str
    canonical_mwh: float | None
    cost_usd: float | None
    is_cost_only: bool
    is_estimated_read: bool
    conversion_note: str | None


class CsvRowErrorDTO(BaseModel):
    row_index: int
    message: str


class CsvPreviewResponse(BaseModel):
    total_rows: int
    valid_count: int
    error_count: int
    bills: list[CsvBillPreviewDTO]
    errors: list[CsvRowErrorDTO]


class CsvCommitResponse(BaseModel):
    total_rows: int
    committed_count: int
    error_count: int
    # Prior estimated/cost-only reads superseded by a truer same-period read (PRD 5.6).
    superseded_count: int = 0
    # site_ref values in the CSV that didn't match any existing site by name.
    unresolved_site_refs: list[str]


class EstimateRequest(BaseModel):
    floor_area_sqft: float
    reporting_year: int


class EstimateResponse(BaseModel):
    site_id: int
    reporting_year: int
    annual_mwh: float
    intensity_kwh_per_sqft: float
    method_note: str


# --- PDF/OCR document ingestion ---------------------------------------------


class FieldDTO(BaseModel):
    value: str | None = None
    confidence: float = 0.0


class ExtractedMeterDTO(BaseModel):
    meter_number: str | None = None
    energy_carrier: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    raw_quantity: float | None = None
    raw_unit: str | None = None
    canonical_mwh: float | None = None
    cost_usd: float | None = None
    demand_kw: float | None = None
    is_estimated_read: bool = False
    is_cost_only: bool = False
    needs_review: bool = False
    min_confidence: float = 0.0
    review_reasons: list[str] = []


class ExtractDocRequest(BaseModel):
    # The bill file, base64-encoded (keeps ingestion JSON-only, like csv_text).
    file_base64: str
    content_type: str | None = None
    filename: str | None = None


class ExtractDocResponse(BaseModel):
    header: dict[str, FieldDTO]
    meters: list[ExtractedMeterDTO]
    model: str = ""
    error: str | None = None
    # True if any meter needs review or the extraction errored — the UI's gate.
    needs_review: bool = False


class ConfirmedMeterInput(BaseModel):
    """A meter the user reviewed/edited and is committing (post-extraction)."""

    energy_carrier: str
    period_start: str
    period_end: str
    raw_quantity: float | None = None
    raw_unit: str | None = None
    canonical_mwh: float | None = None
    cost_usd: float | None = None
    is_estimated_read: bool = False
    is_cost_only: bool = False


class ImportDocRequest(BaseModel):
    site_id: int
    meters: list[ConfirmedMeterInput]


class ImportDocResponse(BaseModel):
    committed_count: int
    superseded_count: int = 0
    # Meters dropped for an unrecognized carrier (not one the DB accepts).
    skipped_count: int = 0


# --- Calculations -----------------------------------------------------------


class RunCalculationRequest(BaseModel):
    reporting_year: int


class CalculationDTO(BaseModel):
    calc_id: int
    reporting_year: int
    scope: str
    site_id: int | None = None
    location_based_kg_co2e: float
    market_based_kg_co2e: float
    consumption_mwh: float | None = None
    market_tier: str | None = None
    market_fallback_flagged: bool = False
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict) -> "CalculationDTO":
        return cls(
            calc_id=int(row["calc_id"]),
            reporting_year=int(row["reporting_year"]),
            scope=row.get("scope", "entity"),
            site_id=int(row["site_id"]) if row.get("site_id") is not None else None,
            location_based_kg_co2e=float(row["location_based_kg_co2e"]),
            market_based_kg_co2e=float(row["market_based_kg_co2e"]),
            consumption_mwh=(
                float(row["consumption_mwh"])
                if row.get("consumption_mwh") is not None
                else None
            ),
            market_tier=row.get("market_tier"),
            market_fallback_flagged=bool(row.get("market_fallback_flagged", False)),
            created_at=row.get("created_at"),
        )


class RunCalculationResponse(BaseModel):
    calc_id: int
    reporting_year: int
    location_based_kg_co2e: float
    market_based_kg_co2e: float
    consumption_mwh: float
    site_count: int
    market_fallback_site_count: int


# --- Data-quality / coverage scoring (PRD 5.6) ------------------------------


class SiteCoverageDTO(BaseModel):
    site_id: int
    total_mwh: float
    coverage_fraction: float
    has_data: bool


class CoverageResponse(BaseModel):
    total_mwh: float
    coverage_fraction: float  # share of consumption backed by actual data (0..1)
    estimation_fraction: float
    site_count: int
    sites_with_data: int
    sites_missing_data: int
    per_site: list[SiteCoverageDTO]


# --- Reporting: one number, many formats (PRD 5.5) --------------------------


class ReportDestinationDTO(BaseModel):
    key: str
    label: str


class ReportRow(BaseModel):
    field: str
    value: str


class ReportResponse(BaseModel):
    destination: str
    entity: str
    reporting_year: int
    rows: list[ReportRow]
    csv: str


# --- Inbound buyer/CDP request queue (PRD 5.5) ------------------------------

ReportDestinationKey = Literal["standard", "cdp", "amazon"]
BuyerRequestStatus = Literal["open", "answered", "declined"]


class CreateBuyerRequest(BaseModel):
    buyer_name: str
    destination: ReportDestinationKey = "standard"
    reporting_year: int | None = None
    due_date: str | None = None  # ISO date
    notes: str | None = None


class UpdateBuyerRequest(BaseModel):
    status: BuyerRequestStatus | None = None
    destination: ReportDestinationKey | None = None
    due_date: str | None = None
    calc_id: int | None = None
    notes: str | None = None


class BuyerRequestDTO(BaseModel):
    request_id: int
    buyer_name: str
    destination: str
    reporting_year: int | None = None
    due_date: str | None = None
    status: str
    calc_id: int | None = None
    answered_at: str | None = None
    notes: str | None = None
    is_overdue: bool = False
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict) -> "BuyerRequestDTO":
        due = row.get("due_date")
        is_overdue = bool(
            row.get("status") == "open"
            and due
            and date.fromisoformat(str(due)) < date.today()
        )
        return cls(
            request_id=int(row["request_id"]),
            buyer_name=row["buyer_name"],
            destination=row.get("destination", "standard"),
            reporting_year=row.get("reporting_year"),
            due_date=due,
            status=row.get("status", "open"),
            calc_id=int(row["calc_id"]) if row.get("calc_id") is not None else None,
            answered_at=row.get("answered_at"),
            notes=row.get("notes"),
            is_overdue=is_overdue,
            created_at=row.get("created_at"),
        )


# --- Leased-site landlord data-requests (PRD 5.2) ---------------------------

LandlordMethod = Literal["email", "portal", "phone"]
LandlordStatus = Literal["draft", "sent", "responded", "declined", "overdue"]


class CreateLandlordRequest(BaseModel):
    site_id: int
    landlord_contact: str | None = None
    method: LandlordMethod = "email"
    reminder_cadence_days: int = 14
    notes: str | None = None


class UpdateLandlordRequest(BaseModel):
    status: LandlordStatus | None = None
    landlord_contact: str | None = None
    method: LandlordMethod | None = None
    reminder_cadence_days: int | None = None
    returned_data_ref: str | None = None
    notes: str | None = None


class LandlordRequestDTO(BaseModel):
    request_id: int
    site_id: int
    site_name: str | None = None
    landlord_contact: str | None = None
    method: str
    status: str
    sent_at: str | None = None
    responded_at: str | None = None
    reminder_cadence_days: int
    returned_data_ref: str | None = None
    notes: str | None = None
    created_at: str | None = None

    @classmethod
    def from_row(cls, row: dict) -> "LandlordRequestDTO":
        return cls(
            request_id=int(row["request_id"]),
            site_id=int(row["site_id"]),
            site_name=row.get("site_name"),
            landlord_contact=row.get("landlord_contact"),
            method=row.get("method", "email"),
            status=row.get("status", "draft"),
            sent_at=row.get("sent_at"),
            responded_at=row.get("responded_at"),
            reminder_cadence_days=int(row.get("reminder_cadence_days", 14)),
            returned_data_ref=row.get("returned_data_ref"),
            notes=row.get("notes"),
            created_at=row.get("created_at"),
        )
