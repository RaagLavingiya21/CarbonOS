"""CSV bulk-intake parser (pure, DB-free).

Expected columns (case-insensitive): source_name, category, fuel, amount, unit,
and optional miles, model_year, tier, biogenic. `category` is stationary|mobile.
Each row is validated independently; row-level errors don't abort the file. The
route resolves source_name to a source id and runs the calc engine per valid row.
See research/2.3 (intake) and MVP-PRD.md job B (CSV bulk upload).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

REQUIRED_COLUMNS = {"source_name", "category", "fuel", "amount", "unit"}
CATEGORIES = {"stationary", "mobile"}
_TRUE = {"1", "true", "yes", "y", "biogenic"}


@dataclass
class IntakeRow:
    row_index: int              # 1-based line number in the file (header = line 1)
    category: str
    source_name: str
    fuel: str
    amount: float
    unit: str
    miles: float | None = None
    model_year: int | None = None
    tier: int = 4
    biogenic: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass
class ParsedIntake:
    rows: list[IntakeRow]
    file_errors: list[str] = field(default_factory=list)

    @property
    def valid_rows(self) -> list[IntakeRow]:
        return [r for r in self.rows if r.is_valid]


def parse_intake_csv(data: bytes) -> ParsedIntake:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return ParsedIntake([], ["Empty or unreadable CSV."])

    header = {(h or "").strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - header
    if missing:
        return ParsedIntake([], [f"Missing required columns: {', '.join(sorted(missing))}."])

    rows: list[IntakeRow] = []
    for line_no, raw in enumerate(reader, start=2):
        cells = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        rows.append(_parse_row(line_no, cells))
    return ParsedIntake(rows)


def _parse_row(line_no: int, cells: dict[str, str]) -> IntakeRow:
    errors: list[str] = []

    category = cells.get("category", "").lower()
    if category not in CATEGORIES:
        errors.append(f"category must be one of {sorted(CATEGORIES)}")

    source_name = cells.get("source_name", "")
    if not source_name:
        errors.append("source_name is required")

    fuel = cells.get("fuel", "")
    if not fuel:
        errors.append("fuel is required")

    unit = cells.get("unit", "")
    if not unit:
        errors.append("unit is required")

    amount = _to_float(cells.get("amount", ""))
    if amount is None or amount <= 0:
        errors.append("amount must be a positive number")

    miles = _to_float(cells.get("miles", "")) if cells.get("miles") else None
    model_year = _to_int(cells.get("model_year", "")) if cells.get("model_year") else None
    tier = _to_int(cells.get("tier", "")) or 4
    if tier < 1 or tier > 5:
        errors.append("tier must be 1-5")
    biogenic = cells.get("biogenic", "").lower() in _TRUE

    return IntakeRow(
        row_index=line_no,
        category=category,
        source_name=source_name,
        fuel=fuel,
        amount=amount or 0.0,
        unit=unit,
        miles=miles,
        model_year=model_year,
        tier=tier,
        biogenic=biogenic,
        errors=errors,
    )


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: str) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
