#!/usr/bin/env python3
"""Seed Scope 1 global reference data (idempotent).

Loads the GWP versions/values, gas species (+ the R-410A blend), the
EPA-anchored combustion emission-factor library, and reporting-regime config
into the s1_* reference tables. These are shared, world-readable reference rows;
writes go through the service role (which bypasses RLS).

The GWP values and emission factors are imported from the calc engine
(s1_calc.gwp.GWP_100, s1_factors.epa_library.EPA_FACTORS) so the stored
reference data and the computed factors share ONE source of truth and can never
drift. Species/version metadata (CAS numbers, molecular weights, IPCC refs) is
persistence-only and lives here. See research/2.1 and 2.2.

The full model-year mobile matrix, DEFRA, and IPCC fallbacks are ingested later
by the s1_factors DB loader; this seed carries the core US combustion set the
MVP calc engine and golden-file evals need.

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
from s1_calc.gwp import GWP_100
from s1_factors.epa_library import EPA_FACTORS, EPA_HUB_URL

# --- GWP versions (IPCC assessment reports) ---------------------------------
# ar_version, publication_year, ipcc_reference, is_current
GWP_VERSIONS = [
    ("AR4", 2007, "IPCC AR4 WGI (2007)", False),
    ("AR5", 2013, "IPCC AR5 WGI Ch.8 (2013)", False),
    ("AR6", 2021, "IPCC AR6 WGI Table 7.SM.7 (without CCF)", True),
]

# --- Gas species (metadata; GWP numbers come from GWP_100) ------------------
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

# R-410A blend = HFC-32 0.50 + HFC-125 0.50 (mass fractions sum to 1.0).
BLENDS = {
    "R-410A": [("HFC-32", 0.50), ("HFC-125", 0.50)],
}

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

    # GWP values (imported from the canonical GWP_100 table)
    gwp_count = 0
    for ar, species_table in GWP_100.items():
        for species_name, by_source in species_table.items():
            for carbon_source, gwp in by_source.items():
                _upsert(
                    client, "s1_gwp_value",
                    {"gwp_version_id": version_ids[ar],
                     "gas_species_id": species_ids[species_name],
                     "carbon_source": carbon_source},
                    {"gwp_version_id": version_ids[ar],
                     "gas_species_id": species_ids[species_name],
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

    # Emission factors (imported from the canonical EPA_FACTORS list)
    ef_count = 0
    for ef in EPA_FACTORS:
        ef_count += _seed_ef(client, ef)
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


def _seed_ef(client, ef) -> int:
    """Insert an active EF row if the natural key is not already present."""
    q = (
        client.table("s1_ef_record").select("id")
        .eq("fuel_or_activity", ef.fuel_or_activity)
        .eq("source_category", ef.source_category)
        .eq("gas", ef.gas)
        .eq("source_version", ef.source_version)
    )
    q = q.eq("model_year", ef.model_year) if ef.model_year is not None else q.is_("model_year", "null")
    if q.limit(1).execute().data:
        return 0
    client.table("s1_ef_record").insert({
        "fuel_or_activity": ef.fuel_or_activity,
        "source_category": ef.source_category,
        "gas": ef.gas,
        "value": ef.value,
        "unit": ef.unit,
        "hhv": ef.hhv,
        "hhv_unit": ef.hhv_unit,
        "source": ef.source,
        "source_version": ef.source_version,
        "source_url": EPA_HUB_URL,
        "region": ef.region,
        "tier": ef.tier,
        "biogenic": ef.biogenic,
        "model_year": ef.model_year,
        "valid_from": ef.source_version,
    }).execute()
    return 1


if __name__ == "__main__":
    main()
