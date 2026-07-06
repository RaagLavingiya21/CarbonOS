"""Destination field mappings for "one number, many formats" (PRD 5.5).

Each destination is a CONFIG table — an ordered list of (field label, extractor)
pairs mapping the canonical ReportSummary to a buyer/disclosure format. Template
drift is a data change here, never a change to export logic. New destinations =
one more entry in DESTINATIONS. Pure — imports only the summary type.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Callable

from s2_reporting.summary import ReportSummary

_Field = tuple[str, Callable[[ReportSummary], object]]

# CDP Supply Chain / Climate C6 — dual method required.
_CDP_FIELDS: list[_Field] = [
    ("Reporting year", lambda s: s.reporting_year),
    ("C6.3 Scope 2 location-based (metric tons CO2e)", lambda s: s.location_based_tco2e),
    ("C6.3 Scope 2 market-based (metric tons CO2e)", lambda s: s.market_based_tco2e),
    ("C8.2 Electricity consumption (MWh)", lambda s: s.consumption_mwh),
    ("C6.5 Methodology", lambda s: s.methodology),
    ("Data completeness (%)", lambda s: s.data_coverage_pct),
]

# Amazon Supply Chain Standards — requires BOTH location- and market-based.
_AMAZON_FIELDS: list[_Field] = [
    ("Supplier / reporting entity", lambda s: s.entity),
    ("Reporting year", lambda s: s.reporting_year),
    ("Scope 2 location-based (tCO2e)", lambda s: s.location_based_tco2e),
    ("Scope 2 market-based (tCO2e)", lambda s: s.market_based_tco2e),
    ("Electricity consumed (MWh)", lambda s: s.consumption_mwh),
    ("Data completeness (%)", lambda s: s.data_coverage_pct),
]

# Plain location- vs market-based summary.
_STANDARD_FIELDS: list[_Field] = [
    ("Entity", lambda s: s.entity),
    ("Reporting year", lambda s: s.reporting_year),
    ("Scope 2 location-based (tCO2e)", lambda s: s.location_based_tco2e),
    ("Scope 2 market-based (tCO2e)", lambda s: s.market_based_tco2e),
    ("Electricity consumption (MWh)", lambda s: s.consumption_mwh),
    ("Methodology", lambda s: s.methodology),
    ("Data coverage (%)", lambda s: s.data_coverage_pct),
]

DESTINATIONS: dict[str, list[_Field]] = {
    "standard": _STANDARD_FIELDS,
    "cdp": _CDP_FIELDS,
    "amazon": _AMAZON_FIELDS,
}


class UnknownDestinationError(ValueError):
    """Raised when a report destination isn't configured."""


def build_report(summary: ReportSummary, destination: str) -> list[dict]:
    """Return prefilled [{field, value}] rows for a destination."""
    fields = DESTINATIONS.get(destination)
    if fields is None:
        raise UnknownDestinationError(
            f"Unknown destination '{destination}'. Known: {sorted(DESTINATIONS)}."
        )
    return [{"field": label, "value": extract(summary)} for label, extract in fields]


def report_to_csv(rows: list[dict]) -> str:
    """Serialize report rows to CSV text."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["field", "value"])
    for row in rows:
        writer.writerow([row["field"], row["value"]])
    return buffer.getvalue()
