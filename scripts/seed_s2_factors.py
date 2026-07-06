"""Seed the Scope 2 grid emission-factor library from a CSV (service role).

Usage:
    python scripts/seed_s2_factors.py scripts/s2_factors_template.csv

The CSV is the swap-in point for real data: replace the sample template with
official EPA eGRID / IEA / Green-e / AIB values (each row must carry a real
source_citation) and re-run. Upserts on (factor_type, region_code, vintage_year),
so re-running with corrected values is safe.

Required columns: factor_type, region_code, vintage_year, kg_co2e_per_mwh,
source_citation. Optional: publish_year, gwp_set.
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

# Allow running as `python scripts/seed_s2_factors.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

VALID_FACTOR_TYPES = {"egrid", "iea", "greene_residual", "aib_residual", "steam"}
REQUIRED_COLUMNS = (
    "factor_type",
    "region_code",
    "vintage_year",
    "kg_co2e_per_mwh",
    "source_citation",
)


class FactorCsvError(ValueError):
    """Raised on a malformed factor CSV."""


def parse_factor_csv(csv_text: str) -> list[dict]:
    """Parse and validate a factor CSV into upsert-ready rows (pure, testable)."""
    reader = csv.DictReader(io.StringIO(csv_text))
    missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise FactorCsvError(f"CSV missing required column(s): {missing}")

    rows: list[dict] = []
    for index, raw in enumerate(reader, start=1):
        factor_type = (raw["factor_type"] or "").strip().lower()
        if factor_type not in VALID_FACTOR_TYPES:
            raise FactorCsvError(
                f"Row {index}: invalid factor_type '{raw['factor_type']}' "
                f"(must be one of {sorted(VALID_FACTOR_TYPES)})."
            )
        citation = (raw["source_citation"] or "").strip()
        if not citation:
            raise FactorCsvError(f"Row {index}: source_citation is required.")
        try:
            rows.append(
                {
                    "factor_type": factor_type,
                    "region_code": raw["region_code"].strip(),
                    "vintage_year": int(raw["vintage_year"]),
                    "publish_year": int(raw["publish_year"])
                    if raw.get("publish_year")
                    else None,
                    "kg_co2e_per_mwh": float(raw["kg_co2e_per_mwh"]),
                    "gwp_set": (raw.get("gwp_set") or "AR6-GWP100").strip(),
                    "source_citation": citation,
                }
            )
        except ValueError as exc:
            raise FactorCsvError(f"Row {index}: {exc}") from exc
    if not rows:
        raise FactorCsvError("CSV contained no data rows.")
    return rows


def seed_factors(rows: list[dict]) -> int:
    """Upsert factor rows into s2_factor_library via the service role."""
    from db.client import get_service_client

    client = get_service_client()
    client.table("s2_factor_library").upsert(
        rows, on_conflict="factor_type,region_code,vintage_year"
    ).execute()
    return len(rows)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python scripts/seed_s2_factors.py <factors.csv>", file=sys.stderr)
        return 2
    csv_path = Path(argv[1])
    rows = parse_factor_csv(csv_path.read_text())
    count = seed_factors(rows)
    print(f"Seeded {count} factor rows into s2_factor_library.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
