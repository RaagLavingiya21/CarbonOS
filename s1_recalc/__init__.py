"""Scope 1 base-year recalculation (GHG Protocol Chapter 5).

Pure, DB-free. Given a declared base-year total, a significance-threshold policy,
and a list of change events, it decides which changes are *structural* (and so
require the base year to be recalculated) vs *organic* (real growth/decline,
never recalculated), and produces the restated base-year total + an audit trail.
"""

from s1_recalc.recalc import (
    ALL_TRIGGERS,
    ORGANIC_TRIGGERS,
    STRUCTURAL_TRIGGERS,
    EnrichedEvent,
    RecalcAnalysis,
    RecalcEvent,
    analyze_recalc,
    is_structural,
)

__all__ = [
    "ALL_TRIGGERS",
    "ORGANIC_TRIGGERS",
    "STRUCTURAL_TRIGGERS",
    "EnrichedEvent",
    "RecalcAnalysis",
    "RecalcEvent",
    "analyze_recalc",
    "is_structural",
]
