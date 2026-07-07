"""Load + run Scope 2 OCR eval cases and produce a Scorecard.

Two tiers share this loader and the pure scoring in `scoring.py`:

  - Golden (deterministic, CI): `cases/{name}.tool_output.json` is a *recorded*
    model tool response. `run_golden_case` replays it through the real extractor
    (parse → normalize) with no LLM call, and scores against `labels/{name}.json`.
    This is what regression-guards the parsing/normalization/review logic.

  - Live (manual, API-key gated): `run_live_case` calls actual Claude vision on a
    real document (bytes), timing it, then scores identically. Not collected by
    pytest — see `run_live.py`.

Label format (`labels/{name}.json`), also the template for real redacted bills:
{
  "doc": "optional-filename-for-live-tier.pdf",
  "header": {"utility_name": "...", "account_number": "...", "service_address": "..."},
  "meters": [
    {"energy_carrier": "electricity",
     "service_period_start": "2025-01-01", "service_period_end": "2025-01-31",
     "consumption_quantity": 1500, "consumption_unit": "kWh",
     "canonical_mwh": 1.5, "is_estimated_read": false}
  ]
}
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from evals.scope2_ocr.scoring import CaseScore, Scorecard, score_case
from s2_ingestion.ocr import extract_bill_document, normalize_bill, parse_extraction

CASES_DIR = Path(__file__).parent / "cases"
LABELS_DIR = Path(__file__).parent / "labels"


def list_golden_cases() -> list[str]:
    """Case names that have both a recorded tool output and a label."""
    names = []
    for path in sorted(CASES_DIR.glob("*.tool_output.json")):
        name = path.name.removesuffix(".tool_output.json")
        if (LABELS_DIR / f"{name}.json").exists():
            names.append(name)
    return names


def _load_label(name: str) -> dict:
    return json.loads((LABELS_DIR / f"{name}.json").read_text(encoding="utf-8"))


def run_golden_case(name: str) -> CaseScore:
    """Replay a recorded model output through parse+normalize and score it."""
    tool_output = json.loads((CASES_DIR / f"{name}.tool_output.json").read_text(encoding="utf-8"))
    label = _load_label(name)
    extraction = parse_extraction(tool_output)
    rows = normalize_bill(extraction)
    return score_case(name, extraction, rows, label)


def run_golden_scorecard() -> Scorecard:
    card = Scorecard()
    for name in list_golden_cases():
        card.add(run_golden_case(name))
    return card


def run_live_case(name: str, file_bytes: bytes, content_type: str) -> CaseScore:
    """Call real Claude vision on a document, time it, and score vs. the label.

    Requires ANTHROPIC_API_KEY (the default invoke inside extract_bill_document).
    """
    label = _load_label(name)
    started = time.monotonic()
    extraction = extract_bill_document(file_bytes, content_type)
    latency_s = time.monotonic() - started
    rows = normalize_bill(extraction)
    return score_case(name, extraction, rows, label, latency_s=latency_s)


__all__ = [
    "CASES_DIR",
    "LABELS_DIR",
    "list_golden_cases",
    "run_golden_case",
    "run_golden_scorecard",
    "run_live_case",
]
