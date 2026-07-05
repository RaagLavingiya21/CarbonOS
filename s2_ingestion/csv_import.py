"""CSV bulk import of utility bills with guided column mapping (PRD 5.1).

Utilities not covered by an aggregator are imported from a CSV. The caller supplies
a column mapping (canonical field -> source header); each row is validated, dates
parsed, and consumption normalized to canonical MWh via s2_ingestion.normalize.
Cost-only rows (no quantity) are flagged for estimation rather than errored, and
never silently treated as kWh.

Pure business logic — imports only the s2_ingestion.normalize leaf.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime

from s2_ingestion.normalize import UnitConversionError, normalize_to_mwh

REQUIRED_FIELDS = ("site_ref", "period_start", "period_end", "quantity", "unit")
OPTIONAL_FIELDS = ("cost_usd", "account_number", "is_estimated")

_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d")


@dataclass(frozen=True)
class ParsedBill:
    site_ref: str
    period_start: date
    period_end: date
    raw_quantity: float | None
    raw_unit: str | None
    canonical_mwh: float | None
    conversion_note: str | None
    cost_usd: float | None
    account_number: str | None
    is_estimated_read: bool
    is_cost_only: bool


@dataclass(frozen=True)
class RowError:
    row_index: int  # 1-based data row (excludes header)
    message: str


@dataclass
class ImportResult:
    bills: list[ParsedBill] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    total_rows: int = 0


class ColumnMappingError(ValueError):
    """Raised when the mapping omits a required canonical field."""


def _parse_date(value: str) -> date:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date '{value}' (expected e.g. YYYY-MM-DD).")


def _parse_bool(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _parse_float(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(str(value).replace(",", "").strip())


def import_bills_csv(csv_text: str, mapping: dict[str, str]) -> ImportResult:
    """Parse a utility-bill CSV under a canonical->header column mapping."""
    missing = [f for f in REQUIRED_FIELDS if f not in mapping]
    if missing:
        raise ColumnMappingError(f"Mapping missing required field(s): {missing}")

    reader = csv.DictReader(io.StringIO(csv_text))
    result = ImportResult()

    for index, row in enumerate(reader, start=1):
        result.total_rows += 1
        try:
            site_ref = (row.get(mapping["site_ref"]) or "").strip()
            if not site_ref:
                raise ValueError("Missing site reference.")
            period_start = _parse_date(row[mapping["period_start"]])
            period_end = _parse_date(row[mapping["period_end"]])
            if period_end < period_start:
                raise ValueError("period_end precedes period_start.")

            raw_quantity = _parse_float(row.get(mapping["quantity"]))
            raw_unit = (row.get(mapping["unit"]) or "").strip() or None
            cost_usd = (
                _parse_float(row.get(mapping["cost_usd"]))
                if "cost_usd" in mapping
                else None
            )
            account_number = (
                (row.get(mapping["account_number"]) or "").strip() or None
                if "account_number" in mapping
                else None
            )
            is_estimated = (
                _parse_bool(row.get(mapping["is_estimated"]))
                if "is_estimated" in mapping
                else False
            )

            canonical_mwh: float | None = None
            conversion_note: str | None = None
            is_cost_only = raw_quantity is None or raw_quantity == 0.0

            if not is_cost_only:
                if not raw_unit:
                    raise ValueError("Quantity present but unit is missing.")
                normalized = normalize_to_mwh(raw_quantity, raw_unit)
                canonical_mwh = normalized.canonical_mwh
                conversion_note = normalized.conversion_note

            result.bills.append(
                ParsedBill(
                    site_ref=site_ref,
                    period_start=period_start,
                    period_end=period_end,
                    raw_quantity=raw_quantity,
                    raw_unit=raw_unit,
                    canonical_mwh=canonical_mwh,
                    conversion_note=conversion_note,
                    cost_usd=cost_usd,
                    account_number=account_number,
                    is_estimated_read=is_estimated,
                    is_cost_only=is_cost_only,
                )
            )
        except (ValueError, KeyError, UnitConversionError) as exc:
            result.errors.append(RowError(row_index=index, message=str(exc)))

    return result
