# Scope 2 OCR evals

Measures how well `s2_ingestion/ocr.py` extracts utility bills, on two tiers that
share the same scoring (`scoring.py`) so nothing is platform-locked.

## Tiers

| Tier | Input | Runs | LLM? |
|------|-------|------|------|
| **Golden** | `cases/<name>.tool_output.json` (recorded model output) | `pytest evals/scope2_ocr/` — **in CI** | no (deterministic) |
| **Live** | real redacted bill files + labels | `python -m evals.scope2_ocr.run_live <docs_dir>` — manual | yes (Claude vision) |

## Metrics (all emitted; weight later)

- **field_accuracy** — header + per-meter fields matching the label.
- **mwh_within_tol_rate** — normalized MWh within 1% (what the calc engine uses).
- **review_precision / review_recall** — does the `needs_review` flag catch the
  meters that were actually wrong. Recall 1.0 = no wrong meter passed silently;
  use this to **calibrate `REVIEW_THRESHOLD`** empirically.
- **cost_usd / latency_s** — live tier only.

## Adding a real document (live tier)

1. Redact a real bill → `docs/acme_jan.pdf` (keep it out of git if sensitive).
2. Write ground truth → `labels/acme_jan.json` (matched by file stem). Schema:

   ```json
   {
     "header": {"utility_name": "...", "account_number": "...", "service_address": "..."},
     "meters": [
       {"energy_carrier": "electricity",
        "service_period_start": "2025-01-01", "service_period_end": "2025-01-31",
        "consumption_quantity": 1500, "consumption_unit": "kWh",
        "canonical_mwh": 1.5, "is_estimated_read": false}
     ]
   }
   ```

3. `export ANTHROPIC_API_KEY=... && python -m evals.scope2_ocr.run_live docs`
   → prints a JSON scorecard (redirect to a file, or forward to LangSmith).

To promote a real bill into the **golden** (CI) tier without shipping the PDF,
record the model's `tool_output` once into `cases/<name>.tool_output.json`.

## Synthetic corpus + threshold calibration (no real bills needed)

When you have no real bills, generate a synthetic corpus and calibrate
`REVIEW_THRESHOLD` against it. Bills are rendered from known values (Pillow), so
ground truth is exact and `canonical_mwh` comes from the real `normalize_to_mwh`.
Three difficulty tiers (`clean` / `moderate` / `hard`: blur, rotation, low-res,
fading) let the threshold be tuned across a spread of legibility, not just pristine
scans. Everything is deterministic per `--seed`.

```bash
# 1. Generate a corpus (gitignored dir; not committed)
python -m evals.scope2_ocr.generate_corpus --out evals/scope2_ocr/corpus --n 30 --seed 0

# 2. Calibrate (real Claude vision — needs a key; never runs in CI)
export ANTHROPIC_API_KEY=...
python -m evals.scope2_ocr.run_calibration evals/scope2_ocr/corpus
```

`run_calibration` prints the scorecard, a precision/recall **threshold sweep**, and
a **recommended threshold** — the smallest cutoff catching ≥95% of misreads
(`--min-recall`), since a missed misread corrupts the inventory silently. Deploy it
without a code change via `S2_OCR_REVIEW_THRESHOLD` (read by `s2_ingestion/ocr.py`).

### Optional: LangSmith experiment tracking

Opt-in, **eval-layer only** — `s2_ingestion/ocr.py` never imports LangSmith. Set
`S2_OCR_LANGSMITH=1` + `LANGSMITH_API_KEY` (and optionally `LANGSMITH_PROJECT`,
default `scope2-ocr-calibration`) to also log each calibration run (metrics +
recommended threshold) and push the corpus as a dataset. Unset → fully offline
no-op, identical scorecard. See `langsmith_tracking.py`.
