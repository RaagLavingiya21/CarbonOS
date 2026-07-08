"""Scope 1 reporting layer — GHG Protocol / SB 253 rollup + View Source trace.

Pure, DB-free. Applies GWP (AR version, at reporting time) and the per-entity
consolidation multiplier over stored gas masses to produce the inventory report
content: gross Scope 1 by gas, by facility, with biogenic CO2 as a separate memo
line. The same content is the SB 253 disclosure body (research/2.4). Switching
ar_version recomputes from identical stored masses — no mutation.
"""

from s1_reporting.export import DisclosureMeta, build_pdf, build_xlsx
from s1_reporting.report import (
    FacilityBreakdown,
    GasBreakdown,
    InventoryReport,
    ReportRecord,
    build_inventory_report,
    trace_record,
)
from s1_reporting.trends import (
    InventoryDatum,
    TrendPoint,
    TrendsResult,
    build_trends,
)

__all__ = [
    "DisclosureMeta",
    "FacilityBreakdown",
    "GasBreakdown",
    "InventoryDatum",
    "InventoryReport",
    "ReportRecord",
    "TrendPoint",
    "TrendsResult",
    "build_inventory_report",
    "build_pdf",
    "build_trends",
    "build_xlsx",
    "trace_record",
]
