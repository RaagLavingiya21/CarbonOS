"""Generate a synthetic Scope 2 OCR corpus on demand.

    python -m evals.scope2_ocr.generate_corpus --out evals/scope2_ocr/corpus --n 30 --seed 0

Writes `<out>/<name>.png` bill images plus a co-located `<out>/<name>.json`
ground-truth label per bill, mixing utilities, carriers/units, meter counts, and
the clean/moderate/hard difficulty tiers. Deterministic for a given `--seed`.

Corpora are generated into a **gitignored** dir (`evals/scope2_ocr/corpus/`) and
consumed by `run_calibration.py` — we commit only a few golden cases, not hundreds
of PNGs, so the repo stays lean.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from evals.scope2_ocr.synthetic import DIFFICULTIES, BillSpec, MeterSpec, generate_bill

# (utility name, city) — kept short and legible.
_UTILITIES = [
    ("PG&E", "San Francisco, CA"),
    ("Con Edison", "New York, NY"),
    ("Duke Energy", "Charlotte, NC"),
    ("ComEd", "Chicago, IL"),
]

# (carrier, printed unit, (low, high) quantity range).
_CARRIERS = [
    ("electricity", "kWh", (800, 5200)),
    ("electricity", "MWh", (1, 20)),
    ("natural_gas", "therms", (200, 1500)),
    ("natural_gas", "MMBtu", (20, 320)),
]

_PERIODS = [
    ("2025-01-01", "2025-01-31"),
    ("2025-02-01", "2025-02-28"),
    ("2025-03-01", "2025-03-31"),
    ("2025-04-01", "2025-04-30"),
]


def _meter(rng: random.Random, idx: int) -> MeterSpec:
    carrier, unit, (lo, hi) = _CARRIERS[rng.randrange(len(_CARRIERS))]
    qty = round(rng.uniform(lo, hi), 1)
    start, end = _PERIODS[rng.randrange(len(_PERIODS))]
    return MeterSpec(
        energy_carrier=carrier,
        service_period_start=start,
        service_period_end=end,
        consumption_quantity=qty,
        consumption_unit=unit,
        is_estimated_read=(rng.random() < 0.25),
        meter_number=f"MTR-{1000 + idx}",
        total_cost_usd=round(qty * rng.uniform(0.08, 0.22), 2),
    )


def build_specs(n: int, seed: int) -> list[tuple[str, BillSpec, str]]:
    """Deterministically build `n` (name, spec, difficulty) triples."""
    triples: list[tuple[str, BillSpec, str]] = []
    for i in range(n):
        rng = random.Random(seed * 100_003 + i)
        difficulty = DIFFICULTIES[i % len(DIFFICULTIES)]
        utility, city = _UTILITIES[rng.randrange(len(_UTILITIES))]
        n_meters = 2 if (i % 3 == 0) else 1
        meters = [_meter(rng, i * 10 + j) for j in range(n_meters)]
        spec = BillSpec(
            utility_name=utility,
            account_number=f"{rng.randrange(10_000_000, 99_999_999)}",
            service_address=f"{rng.randrange(1, 9999)} Market St, {city}",
            meters=meters,
        )
        triples.append((f"{difficulty}_{i:03d}", spec, difficulty))
    return triples


def write_corpus(out_dir: Path, n: int, seed: int) -> dict[str, dict]:
    """Generate + write the corpus; return {name: label} for downstream use."""
    out_dir.mkdir(parents=True, exist_ok=True)
    labels: dict[str, dict] = {}
    for i, (name, spec, difficulty) in enumerate(build_specs(n, seed)):
        bill = generate_bill(spec, difficulty=difficulty, seed=seed * 7919 + i, name=name)
        (out_dir / f"{name}.png").write_bytes(bill.png_bytes)
        (out_dir / f"{name}.json").write_text(json.dumps(bill.label, indent=2), encoding="utf-8")
        labels[name] = bill.label
    return labels


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a synthetic Scope 2 OCR corpus.")
    parser.add_argument("--out", default="evals/scope2_ocr/corpus", help="output directory")
    parser.add_argument("--n", type=int, default=30, help="number of bills")
    parser.add_argument("--seed", type=int, default=0, help="RNG seed (reproducible)")
    args = parser.parse_args()

    out_dir = Path(args.out)
    labels = write_corpus(out_dir, args.n, args.seed)
    print(f"Wrote {len(labels)} bills + labels to {out_dir}/ (seed={args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
