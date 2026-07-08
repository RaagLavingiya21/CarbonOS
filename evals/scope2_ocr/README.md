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
