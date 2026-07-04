#!/usr/bin/env python3
"""Seed Scope 1 global reference data (idempotent).

Loads the GWP versions/values, gas species (+ the R-410A blend), the
EPA-anchored combustion emission-factor library, and reporting-regime config
into the s1_* reference tables. These are shared, world-readable reference rows;
writes go through the service role (which bypasses RLS).

Values are sourced from research/2.1 (combustion + EF library), research/2.2
(GWP seed), and 40 CFR Part 98 Tables C-1/C-2 + the EPA EF Hub 2025. Superseded
rows are never deleted; re-running this script only inserts what is missing.

The full model-year mobile CH4/N2O matrix (EPA Hub Tables 3-5), DEFRA, and IPCC
fallbacks are ingested later by the s1_factors module; this seed carries the core
US combustion set the MVP calc engine and golden-file evals need.

Usage:
    python scripts/seed_scope1_reference.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from db.client import get_service_client

EF_SOURCE_VERSION = "2025-01-15"  # EPA EF Hub 2025 release date

# --- GWP versions (IPCC assessment reports) ---------------------------------
GWP_VERSIONS = [
    # ar_version, publication_year, ipcc_reference, is_current
    ("AR4", 2007, "IPCC AR4 WGI (2007)", False),
    ("AR5", 2013, "IPCC AR5 WGI Ch.8 (2013)", False),
    ("AR6", 2021, "IPCC AR6 WGI Table 7.SM.7 (without CCF)", True),
]

# --- Gas species ------------------------------------------------------------
# common_name, cas_number, gas_family, is_blend, molecular_weight
GAS_SPECIES = [
    ("Carbon dioxide", "124-38-9", "CO2", False, 44.010),
    ("Methane", "74-82-8", "CH4", False, 16.040),
    ("Nitrous oxide", "10024-97-2", "N2O", False, 44.010),
    ("Sulfur hexafluoride", "2551-62-4", "SF6", False, 146.060),
    ("Nitrogen trifluoride", "7783-54-2", "NF3", False, 71.000),
    ("HFC-134a", "811-97-2", "HFC", False, 102.030),
    ("HFC-32", "75-10-5", "HFC", False, 52.020),
    ("HFC-125", "354-33-6", "HFC", False, 120.020),
    ("CF4", "75-73-0", "PFC", False, 88.000),
    ("R-410A", None, "blend", True, None),
]

# --- GWP-100 values, carbon_source = 'all' unless noted ---------------------
# common_name -> gwp_100 for the single-value species (CH4 handled separately).
GWP_ALL = {
    "AR4": {
        "Carbon dioxide": 1, "Nitrous oxide": 298, "Sulfur hexafluoride": 22800,
        "Nitrogen trifluoride": 17200, "HFC-134a": 1430, "HFC-32": 675,
        "HFC-125": 3500, "CF4": 7390,
    },
    "AR5": {
        "Carbon dioxide": 1, "Nitrous oxide": 265, "Sulfur hexafluoride": 23500,
        "Nitrogen trifluoride": 16100, "HFC-134a": 1430, "HFC-32": 677,
        "HFC-125": 3170, "CF4": 6630,
    },
    "AR6": {
        "Carbon dioxide": 1, "Nitrous oxide": 273, "Sulfur hexafluoride": 25200,
        "Nitrogen trifluoride": 17400, "HFC-134a": 1526, "HFC-32": 771,
        "HFC-125": 3740, "CF4": 7380,
    },
}
# CH4 is version-specific and AR6 splits fossil vs biogenic.
# (ar_version, carbon_source, gwp_100)
GWP_CH4 = [
    ("AR4", "all", 25),
    ("AR5", "all", 28),
    ("AR6", "fossil", 29.8),
    ("AR6", "biogenic", 27.9),
]

# R-410A blend = HFC-32 0.50 + HFC-125 0.50 (mass fractions sum to 1.0).
BLENDS = {
    "R-410A": [("HFC-32", 0.50), ("HFC-125", 0.50)],
}

# --- Emission-factor library (EPA EF Hub 2025 + 40 CFR Part 98) --------------
# Stationary CO2 (Table C-1, kg CO2/mmBtu) with default HHV, and shared CH4/N2O
# (Table C-2, kg/mmBtu). fuel_or_activity, CO2 EF, hhv, hhv_unit, ch4_n2o_category
STATIONARY_FUELS = [
    # fuel_or_activity, co2_kg_per_mmbtu, hhv, hhv_unit, cat
    ("natural_gas", 53.06, 1.026e-3, "mmBtu/scf", "natural_gas"),
    ("diesel_no2", 73.96, 0.138, "mmBtu/gal", "petroleum"),
    ("propane", 62.87, 0.091, "mmBtu/gal", "petroleum"),
    ("residual_oil_no6", 75.10, 0.150, "mmBtu/gal", "petroleum"),
    ("bituminous_coal", 93.28, 24.93, "mmBtu/ton", "coal"),
    ("subbituminous_coal", 97.17, 17.25, "mmBtu/ton", "coal"),
    ("anthracite", 103.69, 25.09, "mmBtu/ton", "coal"),
]
# CH4/N2O category (kg/mmBtu) shared across the fuels in that category (Table C-2).
STATIONARY_CH4_N2O = {
    "natural_gas": (1.0e-3, 1.0e-4),
    "petroleum": (3.0e-3, 6.0e-4),
    "coal": (1.1e-2, 1.6e-3),
    "solid_biomass": (3.2e-2, 4.2e-3),
    "gaseous_biomass": (3.2e-3, 6.3e-4),
}
# Mobile CO2 (EPA Hub 2025 Table 2). fuel_or_activity, value, unit, biogenic
MOBILE_CO2 = [
    ("motor_gasoline", 8.78, "kg/gal", False),
    ("diesel", 10.21, "kg/gal", False),
    ("lpg", 5.68, "kg/gal", False),
    ("cng", 0.05444, "kg/scf", False),
    ("lng", 4.50, "kg/gal", False),
    ("biodiesel_b100", 9.45, "kg/gal", True),
    ("ethanol_e100", 5.75, "kg/gal", True),
    ("jet_fuel", 9.75, "kg/gal", False),
]
# Mobile on-road CH4/N2O distance EFs (g/mile), model-year specific. Core rows
# for the calc engine + golden-file evals; the full matrix is ingested later.
# fuel_or_activity, gas, value(g/mile), model_year
MOBILE_DISTANCE = [
    ("gasoline_passenger_car", "CH4", 0.0050, 2022),
    ("gasoline_passenger_car", "N2O", 0.0014, 2022),
    ("gasoline_passenger_car", "N2O", 0.0600, 1995),  # older TWC ~10x N2O
]

# --- Reporting-regime config ------------------------------------------------
# regime_name, gwp ar_version (None => hybrid), gwp_hybrid_rule
REGIMES = [
    ("GHG_Protocol", "AR5", None),
    ("CA_SB_253", "AR5", None),
    ("ESRS_E1", "AR6", None),
    ("EPA_GHGRP", None, "prefer_ar5_fallback_ar6"),
    ("CDP", "AR6", None),
]


def _upsert(client, table, match, row):
    """Insert row if no existing row matches the `match` dict. Returns the id."""
    q = client.table(table).select("id")
    for k, v in match.items():
        q = q.eq(k, v)
    existing = q.limit(1).execute()
    if existing.data:
        return existing.data[0]["id"]
    resp = client.table(table).insert(row).execute()
    return resp.data[0]["id"]


def main() -> None:
    client = get_service_client()

    # GWP versions
    version_ids: dict[str, str] = {}
    for ar, year, ref, current in GWP_VERSIONS:
        version_ids[ar] = _upsert(
            client, "s1_gwp_version", {"ar_version": ar},
            {"ar_version": ar, "publication_year": year,
             "ipcc_reference": ref, "is_current": current},
        )
    print(f"gwp_version: {len(version_ids)} rows")

    # Gas species
    species_ids: dict[str, str] = {}
    for name, cas, family, is_blend, mw in GAS_SPECIES:
        species_ids[name] = _upsert(
            client, "s1_gas_species", {"common_name": name},
            {"common_name": name, "cas_number": cas, "gas_family": family,
             "is_blend": is_blend, "molecular_weight": mw},
        )
    print(f"gas_species: {len(species_ids)} rows")

    # GWP values (single-value species)
    gwp_count = 0
    for ar, values in GWP_ALL.items():
        for name, gwp in values.items():
            _upsert(
                client, "s1_gwp_value",
                {"gwp_version_id": version_ids[ar],
                 "gas_species_id": species_ids[name], "carbon_source": "all"},
                {"gwp_version_id": version_ids[ar],
                 "gas_species_id": species_ids[name],
                 "carbon_source": "all", "gwp_100": gwp},
            )
            gwp_count += 1
    # CH4 (version-specific; AR6 fossil/biogenic split)
    for ar, carbon_source, gwp in GWP_CH4:
        _upsert(
            client, "s1_gwp_value",
            {"gwp_version_id": version_ids[ar],
             "gas_species_id": species_ids["Methane"], "carbon_source": carbon_source},
            {"gwp_version_id": version_ids[ar],
             "gas_species_id": species_ids["Methane"],
             "carbon_source": carbon_source, "gwp_100": gwp},
        )
        gwp_count += 1
    print(f"gwp_value: {gwp_count} rows")

    # Blend components
    blend_count = 0
    for blend_name, components in BLENDS.items():
        for comp_name, fraction in components:
            existing = (
                client.table("s1_gas_blend_component")
                .select("blend_id")
                .eq("blend_id", species_ids[blend_name])
                .eq("component_id", species_ids[comp_name])
                .limit(1).execute()
            )
            if not existing.data:
                client.table("s1_gas_blend_component").insert({
                    "blend_id": species_ids[blend_name],
                    "component_id": species_ids[comp_name],
                    "mass_fraction": fraction,
                }).execute()
            blend_count += 1
    print(f"gas_blend_component: {blend_count} rows")

    # Emission factors — stationary CO2 + CH4/N2O
    ef_count = 0
    for fuel, co2, hhv, hhv_unit, cat in STATIONARY_FUELS:
        ef_count += _seed_ef(
            client, fuel, "stationary_combustion", "CO2", co2, "kg/mmBtu",
            hhv=hhv, hhv_unit=hhv_unit, source="40 CFR Part 98 Table C-1")
        ch4, n2o = STATIONARY_CH4_N2O[cat]
        ef_count += _seed_ef(
            client, fuel, "stationary_combustion", "CH4", ch4, "kg/mmBtu",
            hhv=hhv, hhv_unit=hhv_unit, source="40 CFR Part 98 Table C-2")
        ef_count += _seed_ef(
            client, fuel, "stationary_combustion", "N2O", n2o, "kg/mmBtu",
            hhv=hhv, hhv_unit=hhv_unit, source="40 CFR Part 98 Table C-2")
    # Mobile CO2 (fuel-based)
    for fuel, value, unit, biogenic in MOBILE_CO2:
        ef_count += _seed_ef(
            client, fuel, "mobile_combustion", "CO2", value, unit,
            source="EPA EF Hub 2025 Table 2", biogenic=biogenic)
    # Mobile on-road CH4/N2O (distance-based, model-year specific)
    for fuel, gas, value, model_year in MOBILE_DISTANCE:
        ef_count += _seed_ef(
            client, fuel, "mobile_onroad", gas, value, "g/mile",
            source="EPA EF Hub 2025 Tables 3-5", model_year=model_year)
    print(f"ef_record: {ef_count} rows")

    # Reporting-regime config
    for regime, ar, hybrid in REGIMES:
        _upsert(
            client, "s1_reporting_regime_config", {"regime_name": regime},
            {"regime_name": regime,
             "gwp_version_id": version_ids[ar] if ar else None,
             "gwp_hybrid_rule": hybrid},
        )
    print(f"reporting_regime_config: {len(REGIMES)} rows")

    print("Done. Scope 1 reference data seeded.")


def _seed_ef(client, fuel, category, gas, value, unit, *, hhv=None,
             hhv_unit=None, source="", biogenic=False, model_year=None,
             tier=1) -> int:
    """Insert an active EF row if the natural key is not already present."""
    match = {
        "fuel_or_activity": fuel, "source_category": category, "gas": gas,
        "source_version": EF_SOURCE_VERSION,
    }
    q = client.table("s1_ef_record").select("id")
    for k, v in match.items():
        q = q.eq(k, v)
    if model_year is not None:
        q = q.eq("model_year", model_year)
    else:
        q = q.is_("model_year", "null")
    if q.limit(1).execute().data:
        return 0
    client.table("s1_ef_record").insert({
        "fuel_or_activity": fuel, "source_category": category, "gas": gas,
        "value": value, "unit": unit, "hhv": hhv, "hhv_unit": hhv_unit,
        "source": source, "source_version": EF_SOURCE_VERSION,
        "source_url": "https://www.epa.gov/climateleadership/ghg-emission-factors-hub",
        "region": "US", "tier": tier, "biogenic": biogenic,
        "model_year": model_year, "valid_from": "2025-01-15",
    }).execute()
    return 1


if __name__ == "__main__":
    main()
