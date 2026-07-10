"""Regime mappers: DisclosureData + DisclosureMeta -> neutral Disclosure.

Each mapper only *picks datapoints and lays out sections*; rendering + Latin-1
safety live in render.py. Pure, DB-free. Add a regime = add one mapper here.
"""

from __future__ import annotations

from s1_calc.models import GasMasses
from s1_reporting.disclosures.ir import Disclosure, Section
from s1_reporting.report import DisclosureData

GHGRP_THRESHOLD_TCO2E = 25_000.0


def _coversheet(data: DisclosureData, meta) -> Section:
    return Section(
        title="Reporting entity",
        kind="keyvalue",
        rows=[
            ["Reporting entity", meta.entity_name],
            ["Jurisdiction", meta.jurisdiction],
            ["Reporting year", meta.reporting_year],
            ["Reporting period", f"{meta.period_start} to {meta.period_end}"],
            ["Consolidation approach", meta.consolidation_approach.replace("_", " ")],
            ["GWP version", meta.gwp_version],
            ["Base year", meta.base_year],
            ["Generated", _today()],
        ],
    )


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


def _gross_breakdown_table(data: DisclosureData) -> Section:
    """Gross Scope 1 split into combustion / fugitive / process + total."""
    return Section(
        title="Gross Scope 1 by category (tCO2e)",
        kind="table",
        rows=[
            ["Category", "tCO2e"],
            ["Stationary + mobile combustion", round(data.combustion_tco2e, 4)],
            ["Fugitive (refrigerants)", round(data.fugitive_tco2e, 4)],
            ["Process", round(data.process_tco2e, 4)],
            ["Gross Scope 1 (total)", round(data.gross_scope1_tco2e, 4)],
        ],
        emphasize_last=True,
    )


def _combustion_by_gas_table(data: DisclosureData) -> Section:
    g = data.combustion.by_gas
    return Section(
        title="Combustion emissions by gas (tCO2e)",
        kind="table",
        rows=[
            ["Gas", "tCO2e"],
            ["CO2 (fossil)", round(g.co2_fossil_tco2e, 6)],
            ["CH4", round(g.ch4_tco2e, 6)],
            ["N2O", round(g.n2o_tco2e, 6)],
            ["SF6", round(g.sf6_tco2e, 6)],
            ["NF3", round(g.nf3_tco2e, 6)],
            ["Total (combustion)", round(g.total_tco2e, 6)],
        ],
        emphasize_last=True,
    )


def _by_facility_table(data: DisclosureData) -> Section:
    rows: list = [["Facility", "tCO2e"]]
    for fac in data.combustion.by_facility:
        rows.append([fac.facility_name or "Unassigned", round(fac.tco2e, 6)])
    for line in data.fugitive_lines + data.process_lines:
        rows.append([f"{line.facility_name or 'Unassigned'} — {line.label}", round(line.tco2e, 6)])
    return Section(title="Emissions by facility (tCO2e)", kind="table", rows=rows)


def _biogenic_note(data: DisclosureData) -> Section:
    return Section(
        title="", kind="note",
        note=(f"Biogenic CO2 of {data.biogenic_co2_tco2e:,.4f} tCO2e is reported as a separate "
              "memo line and is excluded from the gross Scope 1 total."),
    )


def _methodology_note(meta) -> Section:
    return Section(title="", kind="note", note=f"Methodology: {meta.methodology_summary}")


_STANDARD_LABELS = {
    "ISAE_3410": "ISAE 3410", "ISSA_5000": "ISSA 5000", "ISO_14064-3": "ISO 14064-3",
}


def assurance_line(meta) -> str:
    """Human-readable third-party verification status from the inventory's
    assurance fields; falls back to the placeholder when unset / level=none."""
    level = (getattr(meta, "assurance_level", None) or "none").lower()
    if level not in ("limited", "reasonable"):
        return "Not yet third-party verified"
    line = f"{level.capitalize()} assurance"
    std = _STANDARD_LABELS.get(getattr(meta, "assurance_standard", None) or "",
                               getattr(meta, "assurance_standard", None) or "")
    if std:
        line += f" ({std})"
    if getattr(meta, "assurance_statement_on_file", False):
        line += "; assurance statement on file"
    return line


def _verification_section(meta) -> Section:
    return Section(
        title="Verification / assurance", kind="keyvalue",
        rows=[["Scope 1 verification/assurance status", assurance_line(meta)]],
    )


# --- SB 253 / GHG Protocol (existing export, now gross = all three categories) ---

def map_sb253(data: DisclosureData, meta) -> Disclosure:
    cover, gross = _coversheet(data, meta), _gross_breakdown_table(data)
    by_gas, by_fac = _combustion_by_gas_table(data), _by_facility_table(data)
    biogenic, method = _biogenic_note(data), _methodology_note(meta)
    verification = _verification_section(meta)
    return Disclosure(
        regime="SB 253",
        doc_title="Scope 1 Emissions Disclosure",
        subtitle=f"CA SB 253 / GHG Protocol Corporate Standard  ({data.ar_version})",
        filename_slug="sb253",
        sections=[cover, gross, by_gas, by_fac, verification, biogenic, method],
        sheet_map=[("Disclosure", [cover, gross, verification, biogenic, method]),
                   ("By gas", [by_gas]), ("By facility", [by_fac])],
    )


# --- ESRS E1 (EU / CSRD) ----------------------------------------------------

def map_esrs_e1(data: DisclosureData, meta) -> Disclosure:
    cover = _coversheet(data, meta)
    e16 = Section(
        title="E1-6 — Gross Scope 1 GHG emissions", kind="keyvalue",
        rows=[["Gross Scope 1 (tCO2e)", round(data.gross_scope1_tco2e, 4)],
              ["Consolidation boundary", meta.consolidation_approach.replace("_", " ")],
              ["GWP dataset", meta.gwp_version]],
    )
    gross, by_gas = _gross_breakdown_table(data), _combustion_by_gas_table(data)
    biogenic, method = _biogenic_note(data), _methodology_note(meta)
    verification = _verification_section(meta)
    return Disclosure(
        regime="ESRS E1",
        doc_title="ESRS E1 Climate Change — Scope 1",
        subtitle=f"ESRS E1-6 (CSRD)  ({data.ar_version})",
        filename_slug="esrs-e1",
        sections=[cover, e16, gross, by_gas, verification, biogenic, method],
        sheet_map=[("ESRS E1", [cover, e16, gross, verification, biogenic, method]),
                   ("By gas", [by_gas])],
    )


# --- CDP (investor questionnaire) -------------------------------------------

def map_cdp(data: DisclosureData, meta) -> Disclosure:
    cover = _coversheet(data, meta)
    c61 = Section(
        title="C6.1 — Gross global Scope 1 emissions", kind="keyvalue",
        rows=[["Gross Scope 1 (metric tons CO2e)", round(data.gross_scope1_tco2e, 2)],
              ["Reporting year", meta.reporting_year]],
    )
    gross, by_gas = _gross_breakdown_table(data), _combustion_by_gas_table(data)
    by_fac = _by_facility_table(data)
    verification = Section(
        title="C10 — Verification", kind="keyvalue",
        rows=[["Scope 1 verification/assurance status", assurance_line(meta)],
              ["Methodology", meta.methodology_summary]],
    )
    return Disclosure(
        regime="CDP",
        doc_title="CDP Climate Change — Scope 1",
        subtitle=f"CDP C6 / C7  ({data.ar_version})",
        filename_slug="cdp",
        sections=[cover, c61, gross, by_gas, by_fac, verification],
        sheet_map=[("CDP", [cover, c61, gross, verification]),
                   ("By gas", [by_gas]), ("By facility", [by_fac])],
    )


# --- EPA GHGRP Subpart C (stationary combustion) ----------------------------

def _ghgrp_units_table(data: DisclosureData) -> Section:
    """Per-facility x per-fuel stationary-combustion units with per-gas masses (kg)."""
    agg: dict[tuple, dict] = {}
    for rec in data.report_records:
        key = (rec.facility_name or "Unassigned", rec.fuel or "unspecified")
        m: GasMasses = rec.gas_masses
        acc = agg.setdefault(key, {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "tier": rec.ef_tier or "T1"})
        acc["co2"] += m.kg_co2_fossil
        acc["ch4"] += m.kg_ch4
        acc["n2o"] += m.kg_n2o
    rows: list = [["Facility", "Fuel", "CO2 (kg)", "CH4 (kg)", "N2O (kg)", "Tier"]]
    for (facility, fuel), a in agg.items():
        rows.append([facility, fuel, round(a["co2"], 3), round(a["ch4"], 3),
                     round(a["n2o"], 3), a["tier"]])
    return Section(title="Subpart C — stationary combustion units", kind="table", rows=rows)


def map_ghgrp(data: DisclosureData, meta) -> Disclosure:
    over = data.gross_scope1_tco2e > GHGRP_THRESHOLD_TCO2E
    threshold = Section(
        title="", kind="note",
        note=(f"Gross Scope 1 is {data.gross_scope1_tco2e:,.2f} tCO2e — "
              f"{'AT OR ABOVE' if over else 'below'} the 25,000 tCO2e/yr GHGRP reporting "
              f"threshold (40 CFR Part 98). {'Reporting is likely required.' if over else 'Reporting may not be required.'}"),
    )
    cover, units, method = _coversheet(data, meta), _ghgrp_units_table(data), _methodology_note(meta)
    verification = _verification_section(meta)
    return Disclosure(
        regime="EPA GHGRP Subpart C",
        doc_title="EPA GHGRP — Scope 1 Stationary Combustion",
        subtitle=f"40 CFR Part 98 Subpart C  ({data.ar_version})",
        filename_slug="epa-ghgrp",
        sections=[cover, units, threshold, verification, method],
        sheet_map=[("GHGRP Subpart C", [cover, threshold, verification, method]),
                   ("Units", [units])],
    )


REGIME_MAPPERS = {
    "esrs-e1": map_esrs_e1,
    "cdp": map_cdp,
    "epa-ghgrp": map_ghgrp,
}
