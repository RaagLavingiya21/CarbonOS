"""Map persisted DB rows (plain dicts) to engine domain objects (PRD 5.4).

Keeps the engine and stores decoupled: stores return dicts, the calc route calls
these mappers, the engine consumes typed dataclasses. Pure — imports only the
factor domain type and the engine models.
"""

from __future__ import annotations

from datetime import date

from s2_calc.models import ConsumptionRecord, EnergyAttributeCertificate, SiteProfile
from s2_factors.library import EmissionFactor


def _to_date(value: object) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def site_profile_from_row(row: dict) -> SiteProfile:
    """Derive a SiteProfile from an s2_sites row.

    Location factor: eGRID subregion for US sites that have one, else IEA country.
    Residual default: Green-e (US) or AIB (EU/other) — overridable once the site
    model carries explicit residual config (post-M0).
    """
    country = (row.get("country") or "US").upper()
    egrid = row.get("egrid_subregion")
    iea = row.get("iea_country") or country

    if egrid:
        location_type, location_region = "egrid", egrid
        residual_type, residual_region = "greene_residual", "US"
    else:
        location_type, location_region = "iea", iea
        residual_type, residual_region = "aib_residual", iea

    return SiteProfile(
        site_id=str(row["site_id"]),
        location_factor_type=location_type,
        location_region=location_region,
        residual_factor_type=residual_type,
        residual_region=residual_region,
    )


def consumption_from_bill_row(row: dict) -> ConsumptionRecord | None:
    """Map an active bill row to a ConsumptionRecord.

    Returns None for cost-only / un-normalized bills (they carry no MWh and route
    to estimation instead of the calc engine).
    """
    mwh = row.get("canonical_mwh")
    if mwh is None:
        return None
    return ConsumptionRecord(
        site_id=str(row["site_id"]),
        energy_carrier=row.get("energy_carrier") or "electricity",
        period_start=_to_date(row["period_start"]),
        period_end=_to_date(row["period_end"]),
        mwh=float(mwh),
        is_estimated=bool(row.get("is_estimated_read", False)),
    )


def factor_from_row(row: dict) -> EmissionFactor:
    return EmissionFactor(
        factor_type=row["factor_type"],
        region_code=row["region_code"],
        vintage_year=int(row["vintage_year"]),
        kg_co2e_per_mwh=float(row["kg_co2e_per_mwh"]),
        source_citation=row["source_citation"],
    )


def eac_from_row(row: dict) -> EnergyAttributeCertificate:
    """Map an s2_eac_instruments row to the engine's EAC (evidence booleans included).

    The 6 storable quality-evidence flags default True when absent; same_market and
    vintage_matched are derived at calc time (not stored), so they aren't read here.
    """
    return EnergyAttributeCertificate(
        instrument_id=str(row["instrument_id"]),
        site_id=str(row["site_id"]),
        instrument_type=row.get("instrument_type") or "rec",
        mwh=float(row["mwh"]),
        region_market=row["region_market"],
        vintage_year=int(row["vintage_year"]),
        kg_co2e_per_mwh=float(row.get("kg_co2e_per_mwh") or 0.0),
        specific_generation_attribute=bool(row.get("specific_generation_attribute", True)),
        unique_no_double_count=bool(row.get("unique_no_double_count", True)),
        registry_tracked=bool(row.get("registry_tracked", True)),
        retired_for_buyer=bool(row.get("retired_for_buyer", True)),
        not_an_offset=bool(row.get("not_an_offset", True)),
        transparent=bool(row.get("transparent", True)),
    )
