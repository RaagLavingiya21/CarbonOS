"""GL/ERP spend ingestion, normalization, and flagging (Epic A / unit P.2.2.a).

Mirrors `parsing/bom_parser.py`: takes a company GL/ERP export (CSV) and returns
normalized spend lines plus flags, applying the "Decision Rules for Ambiguous
Inputs" from CLAUDE.md (missing amount -> flag, duplicates -> flag, anomalies ->
flag). It does NOT classify — that is `factors/spend_classifier.py`. Keeping
ingestion and classification separate lets each be tested in isolation.

Real ERP exports use wildly different column names, so a small synonym map
normalizes common headers to canonical fields; callers can override with an
explicit `column_mapping`. This is the MVP answer to the "many ERP formats"
risk (04-epic-a-implementation-plan.md §8) — generic CSV + column mapping,
with dedicated connectors deferred.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

import pandas as pd

MAX_ROWS = 100_000  # corporate GL exports are large (cf. BOM's 500)
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB

# Canonical fields. `description` is the classification signal; `amount_usd`
# drives the calc. Everything else is optional context.
REQUIRED_COLUMNS = {"description", "amount_usd"}
OPTIONAL_COLUMNS = {"gl_account", "vendor", "period", "currency"}

# Common ERP/GL header synonyms -> canonical field. Extend as new formats appear.
_HEADER_SYNONYMS: dict[str, str] = {
    "description": "description",
    "line_description": "description",
    "gl_description": "description",
    "memo": "description",
    "narrative": "description",
    "details": "description",
    "amount_usd": "amount_usd",
    "amount": "amount_usd",
    "usd_amount": "amount_usd",
    "amount_(usd)": "amount_usd",
    "spend": "amount_usd",
    "spend_usd": "amount_usd",
    "net_amount": "amount_usd",
    "gl_account": "gl_account",
    "account": "gl_account",
    "account_code": "gl_account",
    "gl_code": "gl_account",
    "vendor": "vendor",
    "supplier": "vendor",
    "vendor_name": "vendor",
    "payee": "vendor",
    "period": "period",
    "posting_date": "period",
    "date": "period",
    "fiscal_period": "period",
    "currency": "currency",
    "curr": "currency",
    "ccy": "currency",
}

_ANOMALY_RATIO = 10.0


@dataclass
class SpendFlag:
    row_index: int  # 0-based index into ParsedSpend.rows
    field: str
    flag_type: str  # missing | anomalous | duplicate | credit | currency | formatting_fixed
    message: str
    severity: str  # error | warning


@dataclass
class SpendLine:
    row_index: int
    description: str | None
    amount_usd: float | None
    gl_account: str | None
    vendor: str | None
    period: str | None
    currency: str | None
    flags: list[SpendFlag] = field(default_factory=list)


@dataclass
class ParsedSpend:
    rows: list[SpendLine]
    file_errors: list[str]

    @property
    def is_valid(self) -> bool:
        return len(self.file_errors) == 0 and len(self.rows) > 0

    @property
    def flagged_row_indices(self) -> set[int]:
        return {r.row_index for r in self.rows if r.flags}

    @property
    def all_flags(self) -> list[SpendFlag]:
        return [f for r in self.rows for f in r.flags]

    @property
    def total_amount_usd(self) -> float:
        return sum(r.amount_usd for r in self.rows if r.amount_usd is not None)


def parse_spend_csv(
    source: Union[str, Path, bytes, io.IOBase],
    column_mapping: dict[str, str] | None = None,
) -> ParsedSpend:
    """Parse a GL/ERP spend CSV into normalized `SpendLine`s.

    Args:
        source: file path, bytes, or file-like object.
        column_mapping: optional explicit {source_header: canonical_field} that
            overrides the built-in synonym map (source headers are matched after
            lower/underscore normalization).

    Returns a ParsedSpend regardless of validity; check .is_valid / .file_errors.
    """
    raw_df, file_errors = _load_csv(source)
    if file_errors:
        return ParsedSpend(rows=[], file_errors=file_errors)

    raw_df, map_errors = _apply_mapping(raw_df, column_mapping)
    if map_errors:
        return ParsedSpend(rows=[], file_errors=map_errors)

    if len(raw_df) > MAX_ROWS:
        return ParsedSpend(
            rows=[],
            file_errors=[
                f"File has {len(raw_df)} rows; maximum supported is {MAX_ROWS:,}. "
                "Please split the export and upload in batches."
            ],
        )
    if len(raw_df) == 0:
        return ParsedSpend(rows=[], file_errors=["File is empty — no spend rows found."])

    rows = _build_rows(raw_df)
    _flag_duplicates(rows)
    _flag_anomalous_amounts(rows)
    return ParsedSpend(rows=rows, file_errors=[])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_csv(source: Union[str, Path, bytes, io.IOBase]) -> tuple[pd.DataFrame, list[str]]:
    try:
        if isinstance(source, bytes):
            if len(source) > MAX_FILE_BYTES:
                return pd.DataFrame(), [f"File exceeds 50 MB limit ({len(source) / 1e6:.1f} MB)."]
            source = io.BytesIO(source)
        elif isinstance(source, (str, Path)):
            path = Path(source)
            if path.stat().st_size > MAX_FILE_BYTES:
                return pd.DataFrame(), ["File exceeds 50 MB limit."]
        df = pd.read_csv(source, dtype=str, encoding="utf-8", skip_blank_lines=True)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df = df.dropna(how="all")
        return df, []
    except UnicodeDecodeError:
        return pd.DataFrame(), ["File could not be read — ensure it is UTF-8 encoded CSV."]
    except Exception as exc:
        return pd.DataFrame(), [f"Unreadable file: {exc}. Please upload a valid CSV."]


def _apply_mapping(
    df: pd.DataFrame, column_mapping: dict[str, str] | None
) -> tuple[pd.DataFrame, list[str]]:
    """Rename source headers to canonical fields; validate required fields exist."""
    synonyms = dict(_HEADER_SYNONYMS)
    if column_mapping:
        # Normalize override keys the same way headers are normalized.
        for src, canon in column_mapping.items():
            synonyms[src.strip().lower().replace(" ", "_")] = canon

    renamed = {col: synonyms[col] for col in df.columns if col in synonyms}
    df = df.rename(columns=renamed)
    # Drop duplicate canonical columns (keep first) to avoid ambiguity.
    df = df.loc[:, ~df.columns.duplicated()]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        cols = ", ".join(sorted(missing))
        return df, [
            f"Could not identify required column(s): {cols}. "
            "Provide a column_mapping (e.g. {'Memo': 'description', 'Amount': 'amount_usd'})."
        ]
    return df, []


def _build_rows(df: pd.DataFrame) -> list[SpendLine]:
    rows: list[SpendLine] = []
    for idx, raw in df.iterrows():
        row_index = int(idx)  # type: ignore[arg-type]
        flags: list[SpendFlag] = []

        description = _clean_str(raw.get("description"))
        gl_account = _clean_str(raw.get("gl_account"))
        vendor = _clean_str(raw.get("vendor"))
        period = _clean_str(raw.get("period"))
        currency = _clean_str(raw.get("currency"))

        amount_usd, a_flags = _parse_amount(raw.get("amount_usd"), row_index)
        flags.extend(a_flags)

        if not description:
            flags.append(
                SpendFlag(
                    row_index=row_index,
                    field="description",
                    flag_type="missing",
                    message="Description is missing — line cannot be classified; review.",
                    severity="error",
                )
            )

        if currency and currency.upper() not in ("USD", "US$", "$"):
            flags.append(
                SpendFlag(
                    row_index=row_index,
                    field="currency",
                    flag_type="currency",
                    message=(
                        f"Currency is '{currency}', not USD. No FX conversion is applied "
                        "in this version — convert to USD or flag for review."
                    ),
                    severity="warning",
                )
            )

        rows.append(
            SpendLine(
                row_index=row_index,
                description=description,
                amount_usd=amount_usd,
                gl_account=gl_account,
                vendor=vendor,
                period=period,
                currency=currency,
                flags=flags,
            )
        )
    return rows


def _clean_str(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    return s if s else None


_MONEY_STRIP = re.compile(r"[,$\s]")


def _parse_amount(raw: object, row_index: int) -> tuple[float | None, list[SpendFlag]]:
    """Parse a spend amount. Handles $/comma formatting and (parenthesized)
    negatives (accounting credits). Missing -> flag; credit -> flag (kept, not
    dropped, so the analyst decides)."""
    flags: list[SpendFlag] = []
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        flags.append(
            SpendFlag(
                row_index=row_index,
                field="amount_usd",
                flag_type="missing",
                message="Amount is missing — line flagged for human review.",
                severity="warning",
            )
        )
        return None, flags

    s = str(raw).strip()
    if not s:
        flags.append(
            SpendFlag(
                row_index=row_index,
                field="amount_usd",
                flag_type="missing",
                message="Amount is missing — line flagged for human review.",
                severity="warning",
            )
        )
        return None, flags

    # Accounting-style negatives: (1,234.56) -> -1234.56
    negative_paren = s.startswith("(") and s.endswith(")")
    cleaned = _MONEY_STRIP.sub("", s.strip("()"))
    try:
        value = float(cleaned)
    except ValueError:
        flags.append(
            SpendFlag(
                row_index=row_index,
                field="amount_usd",
                flag_type="anomalous",
                message=f"Amount '{s}' is not a valid number — flagged for review.",
                severity="error",
            )
        )
        return None, flags

    if negative_paren:
        value = -value

    if value < 0:
        flags.append(
            SpendFlag(
                row_index=row_index,
                field="amount_usd",
                flag_type="credit",
                message=(
                    f"Amount is negative ({value}) — looks like a credit/refund, "
                    "not a purchase. Flagged for review (excluded from spend by default)."
                ),
                severity="warning",
            )
        )
    elif value == 0:
        flags.append(
            SpendFlag(
                row_index=row_index,
                field="amount_usd",
                flag_type="anomalous",
                message="Amount is zero — flagged for review.",
                severity="warning",
            )
        )

    return value, flags


def _flag_duplicates(rows: list[SpendLine]) -> None:
    """Flag rows that look like duplicate postings (same description, vendor,
    amount, period)."""
    seen: dict[tuple, list[int]] = {}
    for row in rows:
        key = (
            (row.description or "").lower().strip(),
            (row.vendor or "").lower().strip(),
            round(row.amount_usd or 0, 2),
            (row.period or "").lower().strip(),
        )
        seen.setdefault(key, []).append(row.row_index)

    for indices in seen.values():
        if len(indices) > 1:
            for idx in indices:
                row = next(r for r in rows if r.row_index == idx)
                others = [i + 1 for i in indices if i != idx]
                row.flags.append(
                    SpendFlag(
                        row_index=idx,
                        field="row",
                        flag_type="duplicate",
                        message=(
                            f"Appears to duplicate row(s) {others} "
                            "(same description, vendor, amount, period). "
                            "Proceeding but flagging for review."
                        ),
                        severity="warning",
                    )
                )


def _flag_anomalous_amounts(rows: list[SpendLine]) -> None:
    """Flag amount outliers using ratio-to-median (>10x or <1/10th)."""
    values = [(r, r.amount_usd) for r in rows if r.amount_usd is not None and r.amount_usd > 0]
    if len(values) < 2:
        return
    nums = sorted(v for _, v in values)
    mid = len(nums) // 2
    median = (nums[mid] + nums[~mid]) / 2
    if median == 0:
        return
    for row, val in values:
        ratio = val / median
        if ratio > _ANOMALY_RATIO or ratio < 1 / _ANOMALY_RATIO:
            if not any(f.field == "amount_usd" and f.flag_type == "anomalous" for f in row.flags):
                direction = "high" if ratio > _ANOMALY_RATIO else "low"
                row.flags.append(
                    SpendFlag(
                        row_index=row.row_index,
                        field="amount_usd",
                        flag_type="anomalous",
                        message=(
                            f"Amount {val} is unusually {direction} (median {median}) "
                            "— flagged for review."
                        ),
                        severity="warning",
                    )
                )
