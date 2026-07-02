#!/usr/bin/env python3
"""Seed a demo product footprint via the real calculation pipeline.

Usage:
    export SEED_USER_ID="<supabase-user-uuid>"
    export SEED_ACCESS_TOKEN="<supabase-access-token>"
    python scripts/seed_demo.py [--bom sample_boms/clean_tshirt.csv]

Reads a sample BOM CSV, runs parse → EF lookup → calculate → critic, then persists
the result with ``db.store.save_analysis``. Re-running creates another product row
(same name is allowed).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from calc.critic import run_critic
from calc.footprint import calculate_footprint
from db.store import save_analysis
from factors.ef_lookup import lookup_ef
from parsing.bom_parser import parse_bom_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a demo saved analysis.")
    parser.add_argument(
        "--bom",
        default="sample_boms/clean_tshirt.csv",
        help="Path to a BOM CSV relative to the repo root (default: clean_tshirt.csv)",
    )
    parser.add_argument(
        "--product-name",
        default=None,
        help="Override product name (defaults to BOM filename stem)",
    )
    args = parser.parse_args()

    user_id = os.environ.get("SEED_USER_ID")
    access_token = os.environ.get("SEED_ACCESS_TOKEN")
    if not user_id or not access_token:
        raise SystemExit("SEED_USER_ID and SEED_ACCESS_TOKEN environment variables are required.")

    bom_path = ROOT / args.bom
    if not bom_path.is_file():
        raise SystemExit(f"BOM file not found: {bom_path}")

    product_name = args.product_name or bom_path.stem.replace("_", " ").title()
    bom = parse_bom_csv(bom_path.read_bytes(), product_name)
    ef_matches = [
        lookup_ef(row.material, row.country_of_origin) if row.material else None
        for row in bom.rows
    ]
    result = calculate_footprint(bom, ef_matches)
    result, _report = run_critic(result)

    product_id = save_analysis(
        product_name,
        result,
        user_id=user_id,
        access_token=access_token,
        analysis_date=date.today(),
        status="approved",
        product_description=f"Demo seed for {product_name}",
    )
    print(f"Saved product_id={product_id} ({product_name})")


if __name__ == "__main__":
    main()
