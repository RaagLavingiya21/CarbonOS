"""Input/output domain types for the Scope 2 dual-method engine (PRD 5.4).

Plain dataclasses with no persistence or UI coupling, so the engine runs from a
plain script or a test. The store layer (migrations 041/045) maps DB rows to these.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ConsumptionRecord:
    """One bill's normalized consumption for a site (already MWh via s2_ingestion)."""

    site_id: str
    energy_carrier: str  # electricity | steam | heat | cooling
    period_start: date
    period_end: date
    mwh: float
    is_estimated: bool = False


@dataclass(frozen=True)
class SiteProfile:
    """Everything the engine needs to pick factors for a site."""

    site_id: str
    location_factor_type: str  # 'egrid' (US) or 'iea' (intl)
    location_region: str  # eGRID subregion code or IEA country code
    residual_factor_type: str | None = None  # 'greene_residual' | 'aib_residual'
    residual_region: str | None = None
    # Optional supplier-specific / green-tariff factor (higher tier than residual).
    supplier_specific_kg_per_mwh: float | None = None
    supplier_specific_citation: str | None = None


@dataclass(frozen=True)
class EnergyAttributeCertificate:
    """A contractual instrument (REC/GO/green tariff) for market-based accounting.

    Evidence fields feed the 8 GHG Protocol quality criteria (s2_calc.instruments).
    same_market and vintage_matched are derived at check time (need site region +
    reporting year), so they are not stored as raw booleans here.
    """

    instrument_id: str
    site_id: str
    instrument_type: str  # rec | go | green_tariff | ppa
    mwh: float
    region_market: str
    vintage_year: int
    kg_co2e_per_mwh: float = 0.0  # unbundled RECs convey a zero rate; PPAs may differ
    specific_generation_attribute: bool = True
    unique_no_double_count: bool = True
    registry_tracked: bool = True
    retired_for_buyer: bool = True
    not_an_offset: bool = True
    transparent: bool = True


@dataclass(frozen=True)
class SiteResult:
    site_id: str
    consumption_mwh: float
    location_based_kg: float
    market_based_kg: float
    location_factor_citation: str
    location_factor_vintage: int
    market_tier: str
    market_fallback_flagged: bool
    excluded_instruments: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DualMethodResult:
    """Two labeled totals — never merged or averaged (PRD 5.4)."""

    location_based_kg_co2e: float
    market_based_kg_co2e: float
    reporting_year: int
    site_results: list[SiteResult] = field(default_factory=list)
    audit_entries: list[dict] = field(default_factory=list)
