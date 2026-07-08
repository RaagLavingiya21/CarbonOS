"""Live REVIEW_THRESHOLD calibration over a synthetic (or real) OCR corpus.

    export ANTHROPIC_API_KEY=...
    python -m evals.scope2_ocr.generate_corpus --out evals/scope2_ocr/corpus --n 30
    python -m evals.scope2_ocr.run_calibration evals/scope2_ocr/corpus

Runs the real Claude-vision extractor over each `<corpus>/<name>.png` (scored
against the co-located `<name>.json` label), aggregates a Scorecard, and sweeps the
review-confidence cutoff to recommend a `REVIEW_THRESHOLD`. Prints a JSON report to
stdout. This makes real API calls and is non-deterministic, so it is a script — not
a pytest-collected test — and never runs in CI.

Opt-in LangSmith tracking: set `S2_OCR_LANGSMITH=1` + `LANGSMITH_API_KEY` to also
log the run (metrics + recommended threshold) and push the corpus as a dataset. See
`langsmith_tracking.py`. With those unset the run is identical and fully local.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from evals.scope2_ocr import langsmith_tracking as ls
from evals.scope2_ocr.calibration import (
    Observation,
    observations_from_rows,
    recommend_threshold,
    sweep_threshold,
)
from evals.scope2_ocr.scoring import Scorecard, score_case
from s2_ingestion.ocr import extract_bill_document, normalize_bill

_CONTENT_TYPE = "image/png"


def run(corpus_dir: Path, *, min_recall: float) -> dict:
    """Extract + score every bill, then sweep the review threshold."""
    extract = ls.traced_extract(extract_bill_document)  # traced only when enabled
    card = Scorecard()
    observations: list[Observation] = []
    labels: dict[str, dict] = {}

    for image in sorted(corpus_dir.glob("*.png")):
        name = image.stem
        label_path = corpus_dir / f"{name}.json"
        if not label_path.exists():
            print(f"skip {image.name}: no {name}.json", file=sys.stderr)
            continue
        label = json.loads(label_path.read_text(encoding="utf-8"))
        labels[name] = label

        started = time.monotonic()
        extraction = extract(image.read_bytes(), _CONTENT_TYPE)
        latency_s = time.monotonic() - started
        rows = normalize_bill(extraction)

        card.add(score_case(name, extraction, rows, label, latency_s=latency_s))
        observations.extend(observations_from_rows(rows, label))

    summary = card.summary()
    sweep = [p.to_dict() for p in sweep_threshold(observations)]
    recommended = recommend_threshold(observations, min_recall=min_recall)

    report = {
        "corpus": str(corpus_dir),
        "n_meters": len(observations),
        "min_recall_target": min_recall,
        "recommended_threshold": recommended,
        "scorecard": summary,
        "threshold_sweep": sweep,
    }

    if ls.is_enabled():
        ls.upload_corpus_dataset(str(corpus_dir), labels)
        ls.log_experiment(
            summary,
            threshold=recommended,
            metadata={
                "corpus": str(corpus_dir),
                "n_meters": len(observations),
                "min_recall": min_recall,
            },
        )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate REVIEW_THRESHOLD over an OCR corpus.")
    parser.add_argument("corpus_dir", help="directory of <name>.png + <name>.json pairs")
    parser.add_argument("--min-recall", type=float, default=0.95, help="review-recall floor")
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir)
    if not corpus_dir.is_dir():
        print(f"not a directory: {corpus_dir}", file=sys.stderr)
        return 2
    if not (os.getenv("ANTHROPIC_API_KEY")):
        print(
            "warning: ANTHROPIC_API_KEY not set — extractions will be flagged errors",
            file=sys.stderr,
        )

    print(json.dumps(run(corpus_dir, min_recall=args.min_recall), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
