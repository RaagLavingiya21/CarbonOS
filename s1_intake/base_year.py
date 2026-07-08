"""Base-year import parser (pure, DB-free).

A lead migrating off a consultant/spreadsheet imports their prior-year inventory
TOTAL to set the base year (MVP-PRD.md job A1b). Expected CSV columns
(case-insensitive): base_year, total_tco2e, and optional gwp_version
(AR4|AR5|AR6, default AR5). The first data row is used. The value lands on
s1_inventory.base_year / base_year_total_tco2e / base_year_gwp_version (existing
columns — no new migration), with the source file kept as evidence.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

REQUIRED_COLUMNS = {"base_year", "total_tco2e"}
_GWP_VERSIONS = {"AR4", "AR5", "AR6"}


@dataclass
class BaseYearImport:
    base_year: int | None = None
    total_tco2e: float | None = None
    gwp_version: str = "AR5"
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors and self.base_year is not None and self.total_tco2e is not None


def parse_base_year_csv(data: bytes) -> BaseYearImport:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return BaseYearImport(errors=["Empty or unreadable CSV."])

    header = {(h or "").strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - header
    if missing:
        return BaseYearImport(errors=[f"Missing required columns: {', '.join(sorted(missing))}."])

    first = next(reader, None)
    if first is None:
        return BaseYearImport(errors=["No data rows in the CSV."])

    cells = {(k or "").strip().lower(): (v or "").strip() for k, v in first.items()}
    errors: list[str] = []

    base_year = _to_int(cells.get("base_year", ""))
    if base_year is None:
        errors.append("base_year must be an integer year")

    total = _to_float(cells.get("total_tco2e", ""))
    if total is None or total < 0:
        errors.append("total_tco2e must be a non-negative number")

    gwp = (cells.get("gwp_version", "") or "AR5").upper()
    if gwp not in _GWP_VERSIONS:
        gwp = "AR5"

    return BaseYearImport(base_year=base_year, total_tco2e=total, gwp_version=gwp, errors=errors)


def _to_int(value: str) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
