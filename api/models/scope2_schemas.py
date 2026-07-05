"""Pydantic request/response models for the Scope 2 ("Grid") API layer.

Kept separate from api/models/schemas.py so the Scope 2 module shares no domain
types with the Carbon OS (Scope 3 / PACT) product. Only infra types (auth, health)
are shared at the app level.
"""

from __future__ import annotations

from pydantic import BaseModel

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
