"""Regulatory Scope 2 disclosure generators (PRD V1 — compliance-grade).

Where s2_reporting.formats prefills flat buyer templates (CDP, Amazon), this module
produces *structured* regulatory disclosures for the two Scope 2 regimes a mid-market
consumer company hits first:

  - **CA SB 253** (Climate Corporate Data Accountability Act) — Scope 1 & 2 per the
    GHG Protocol, third-party assured. Scope 2 is disclosed dual-method (location-
    based, and market-based where contractual instruments exist).
  - **CSRD ESRS E1** — E1-6 requires gross Scope 2 in **both** location-based and
    market-based methods; E1-5 requires energy consumption + renewable mix.

Both regimes consume the same canonical figures (LB tCO2e, MB tCO2e, consumption
MWh) plus entity/boundary metadata. A disclosure is a list of titled sections, not a
flat row list, so it reads like a filing. Each carries an **assurance-readiness**
gate: blockers (hard gaps that make the figure unreportable) and warnings (soft gaps
an assurer will question) — computed from the calc, not asserted.

Template/standard drift is a data change to the builders here, never a change to
export logic. Pure — imports only the summary type.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from s2_reporting.summary import ReportSummary

# Data-coverage below this (%) is a blocker; below the assurance target is a warning.
_COVERAGE_FLOOR_PCT = 50.0
_COVERAGE_ASSURANCE_PCT = 95.0


@dataclass(frozen=True)
class DisclosureContext:
    """Regulatory metadata not held on the calc row (resolved in the route layer)."""

    consolidation_approach: str = "operational_control"
    gwp_version: str = "IPCC AR5 (100-year GWP)"
    assurance_status: str = "not yet assured"  # e.g. "limited assurance obtained"
    base_year: int | None = None
    renewable_mwh: float | None = None  # ESRS E1-5 energy mix; None = not yet tracked


@dataclass(frozen=True)
class DisclosureItem:
    label: str
    value: object
    note: str | None = None


@dataclass(frozen=True)
class DisclosureSection:
    title: str
    items: list[DisclosureItem]


@dataclass(frozen=True)
class ReadinessCheck:
    blockers: list[str] = field(default_factory=list)  # make the figure unreportable
    warnings: list[str] = field(default_factory=list)  # an assurer will question

    @property
    def ready(self) -> bool:
        return not self.blockers


@dataclass(frozen=True)
class ComplianceDisclosure:
    standard: str
    standard_label: str
    entity: str
    reporting_year: int
    sections: list[DisclosureSection]
    readiness: ReadinessCheck


def _pct(value: float) -> str:
    return f"{value:g}%"


def _t(value: float) -> str:
    return f"{value:,.3f} tCO2e"


def _assess_readiness(
    summary: ReportSummary,
    ctx: DisclosureContext,
    *,
    standard_label: str,
    require_energy_mix: bool,
) -> ReadinessCheck:
    """Shared assurance-readiness gate over the canonical figures."""
    blockers: list[str] = []
    warnings: list[str] = []

    if summary.consumption_mwh <= 0:
        blockers.append("No Scope 2 energy consumption recorded for the period.")
    if summary.data_coverage_pct < _COVERAGE_FLOOR_PCT:
        blockers.append(
            f"Data coverage {_pct(summary.data_coverage_pct)} is below a reportable "
            f"threshold ({_pct(_COVERAGE_FLOOR_PCT)})."
        )
    elif summary.data_coverage_pct < _COVERAGE_ASSURANCE_PCT:
        warnings.append(
            f"Data coverage {_pct(summary.data_coverage_pct)} is below the "
            f"{_pct(_COVERAGE_ASSURANCE_PCT)} assurance target."
        )

    if summary.market_based_fallback:
        warnings.append(
            "Market-based total fell back to grid/residual mix — no contractual "
            "instruments; the market-based figure is not substantiated by EACs."
        )
    if "assured" not in ctx.assurance_status.lower() or "not" in ctx.assurance_status.lower():
        warnings.append(f"Third-party assurance pending (required by {standard_label}).")
    if require_energy_mix and ctx.renewable_mwh is None:
        warnings.append(
            "Renewable energy share not tracked — required for ESRS E1-5 energy mix."
        )
    return ReadinessCheck(blockers=blockers, warnings=warnings)


def _entity_section(summary: ReportSummary, ctx: DisclosureContext, framework: str) -> DisclosureSection:
    items = [
        DisclosureItem("Reporting entity", summary.entity),
        DisclosureItem("Framework", framework),
        DisclosureItem("Reporting year", summary.reporting_year),
        DisclosureItem("Organizational boundary", ctx.consolidation_approach.replace("_", " ")),
        DisclosureItem("GWP version", ctx.gwp_version),
    ]
    if ctx.base_year is not None:
        items.append(DisclosureItem("Base year", ctx.base_year))
    return DisclosureSection("Entity & basis of preparation", items)


def build_sb253(summary: ReportSummary, ctx: DisclosureContext) -> ComplianceDisclosure:
    label = "CA SB 253 (CCDAA)"
    sections = [
        _entity_section(summary, ctx, "California SB 253 / GHG Protocol Corporate Standard"),
        DisclosureSection(
            "Scope 2 emissions (GHG Protocol dual method)",
            [
                DisclosureItem("Scope 2 location-based", _t(summary.location_based_tco2e)),
                DisclosureItem(
                    "Scope 2 market-based",
                    _t(summary.market_based_tco2e),
                    note="grid/residual fallback — no contractual instruments"
                    if summary.market_based_fallback
                    else None,
                ),
                DisclosureItem("Electricity consumption", f"{summary.consumption_mwh:,.3f} MWh"),
            ],
        ),
        DisclosureSection(
            "Methodology & assurance",
            [
                DisclosureItem("Methodology", summary.methodology),
                DisclosureItem("Data coverage", _pct(summary.data_coverage_pct)),
                DisclosureItem("Assurance status", ctx.assurance_status),
            ],
        ),
    ]
    readiness = _assess_readiness(summary, ctx, standard_label=label, require_energy_mix=False)
    return ComplianceDisclosure("sb253", label, summary.entity, summary.reporting_year, sections, readiness)


def build_csrd_e1(summary: ReportSummary, ctx: DisclosureContext) -> ComplianceDisclosure:
    label = "CSRD ESRS E1"
    renewable = ctx.renewable_mwh
    energy_items = [DisclosureItem("Total energy consumption", f"{summary.consumption_mwh:,.3f} MWh")]
    if renewable is not None and summary.consumption_mwh > 0:
        share = renewable / summary.consumption_mwh * 100.0
        energy_items += [
            DisclosureItem("Renewable energy consumption", f"{renewable:,.3f} MWh"),
            DisclosureItem("Renewable share", _pct(round(share, 1))),
            DisclosureItem(
                "Non-renewable energy consumption",
                f"{max(summary.consumption_mwh - renewable, 0.0):,.3f} MWh",
            ),
        ]
    else:
        energy_items.append(
            DisclosureItem("Renewable share", "not tracked", note="pending EAC registry linkage")
        )
    sections = [
        _entity_section(summary, ctx, "ESRS E1 Climate change (CSRD)"),
        DisclosureSection(
            "E1-6 Gross Scope 2 GHG emissions",
            [
                DisclosureItem("Location-based", _t(summary.location_based_tco2e)),
                DisclosureItem(
                    "Market-based",
                    _t(summary.market_based_tco2e),
                    note="grid/residual fallback — no contractual instruments"
                    if summary.market_based_fallback
                    else None,
                ),
            ],
        ),
        DisclosureSection("E1-5 Energy consumption & mix", energy_items),
        DisclosureSection(
            "Methodologies & significant assumptions",
            [
                DisclosureItem("Methodology", summary.methodology),
                DisclosureItem("Data coverage", _pct(summary.data_coverage_pct)),
                DisclosureItem("Assurance status", ctx.assurance_status),
            ],
        ),
    ]
    readiness = _assess_readiness(summary, ctx, standard_label=label, require_energy_mix=True)
    return ComplianceDisclosure("csrd_e1", label, summary.entity, summary.reporting_year, sections, readiness)


_Builder = Callable[[ReportSummary, DisclosureContext], ComplianceDisclosure]

STANDARDS: dict[str, tuple[str, _Builder]] = {
    "sb253": ("CA SB 253 (CCDAA)", build_sb253),
    "csrd_e1": ("CSRD ESRS E1", build_csrd_e1),
}


class UnknownStandardError(ValueError):
    """Raised when a disclosure standard isn't configured."""


def build_disclosure(
    summary: ReportSummary, ctx: DisclosureContext, standard: str
) -> ComplianceDisclosure:
    entry = STANDARDS.get(standard)
    if entry is None:
        raise UnknownStandardError(
            f"Unknown disclosure standard '{standard}'. Known: {sorted(STANDARDS)}."
        )
    return entry[1](summary, ctx)


def disclosure_to_csv(disclosure: ComplianceDisclosure) -> str:
    """Flatten a disclosure to CSV (section, field, value, note)."""
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["section", "field", "value", "note"])
    for section in disclosure.sections:
        for item in section.items:
            writer.writerow([section.title, item.label, item.value, item.note or ""])
    return buffer.getvalue()


__all__ = [
    "DisclosureContext",
    "DisclosureItem",
    "DisclosureSection",
    "ReadinessCheck",
    "ComplianceDisclosure",
    "STANDARDS",
    "UnknownStandardError",
    "build_sb253",
    "build_csrd_e1",
    "build_disclosure",
    "disclosure_to_csv",
]
