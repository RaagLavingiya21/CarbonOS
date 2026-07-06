"""Period proration across irregular billing periods (PRD 5.4).

Utility bills rarely align to calendar years. Each bill's consumption is allocated
to a reporting year by the fraction of its (inclusive) day span that falls inside
that calendar year. Leaf module — imports nothing internal.
"""

from __future__ import annotations

from datetime import date


def _inclusive_days(start: date, end: date) -> int:
    return (end - start).days + 1


def overlap_fraction(period_start: date, period_end: date, reporting_year: int) -> float:
    """Fraction of a billing period that falls within the reporting calendar year."""
    if period_end < period_start:
        raise ValueError("period_end precedes period_start")
    year_start = date(reporting_year, 1, 1)
    year_end = date(reporting_year, 12, 31)
    overlap_start = max(period_start, year_start)
    overlap_end = min(period_end, year_end)
    if overlap_end < overlap_start:
        return 0.0
    return _inclusive_days(overlap_start, overlap_end) / _inclusive_days(
        period_start, period_end
    )


def prorate_mwh(
    mwh: float, period_start: date, period_end: date, reporting_year: int
) -> float:
    """MWh attributable to `reporting_year` for a bill spanning the given period."""
    return mwh * overlap_fraction(period_start, period_end, reporting_year)
