"""SB 253 / GHG Protocol disclosure exports.

Two artifacts over one locked inventory (research/2.4):
  - build_xlsx: structured, field-tagged workbook (the durable mapping layer for
    CARB's eventual 2027 template/portal).
  - build_pdf: a human-readable GHG-Protocol-aligned disclosure with a coversheet.

Both now delegate to the shared regime pipeline (s1_reporting.disclosures): the
SB 253 mapper -> neutral IR -> render_pdf / render_xlsx. They accept either a
bare `InventoryReport` (combustion-only; fugitive/process treated as 0, for
back-compat) or a `DisclosureData` (gross = combustion + fugitive + process).
"""

from __future__ import annotations

from dataclasses import dataclass

from s1_reporting.disclosures.mappers import map_sb253
from s1_reporting.disclosures.render import (  # noqa: F401 (re-export)
    _pdf_safe,
    render_pdf,
    render_xlsx,
)
from s1_reporting.report import DisclosureData, InventoryReport


@dataclass
class DisclosureMeta:
    entity_name: str
    jurisdiction: str
    reporting_year: int
    period_start: str
    period_end: str
    consolidation_approach: str
    gwp_version: str
    base_year: int
    methodology_summary: str = (
        "Fuel-based (GHG Protocol Tier 1); EPA Emission Factors Hub 2025 / "
        "40 CFR Part 98; per-gas masses with GWP applied at reporting time."
    )


def _as_disclosure_data(report: InventoryReport | DisclosureData) -> DisclosureData:
    if isinstance(report, DisclosureData):
        return report
    return DisclosureData(combustion=report)   # combustion-only; fugitive/process = 0


def build_xlsx(report: InventoryReport | DisclosureData, meta: DisclosureMeta) -> bytes:
    return render_xlsx(map_sb253(_as_disclosure_data(report), meta))


def build_pdf(report: InventoryReport | DisclosureData, meta: DisclosureMeta) -> bytes:
    return render_pdf(map_sb253(_as_disclosure_data(report), meta))
