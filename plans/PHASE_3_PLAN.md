# Phase 3 Implementation Plan — Primary Data Loop + PDS

**Executes:** Phase 3 of `PCF_PLATFORM_DESIGN.md`. Read that file and `CLAUDE.md` before starting.
**Branch:** `feature/phase-3-primary-data-loop` (already created off `main`, which has Phase 1 + Phase 2 merged).
**Builds on:** Phase 1 (`line_items.data_source` default `secondary`; `products.primary_data_share` default `0`) and Phase 2 (`product_lineage_id`, `version`, publish lifecycle — see `db/store.py` `save_analysis` lineage logic and migration `021`).
**Outcome:** Verified supplier data flows back into the footprint — a line item flips from secondary (CEDA screening) to primary, the footprint recomputes as a new version, and Primary Data Share (PDS) moves off 0%. Two entry points (supplier-email loop + manual line-item entry), both funnelling through one core primitive, both gated by an analyst confirmation.

## Instructions for the implementer
- Implement exactly what this plan specifies. If something is ambiguous or looks wrong, STOP and report it — do not improvise or redesign.
- Do not refactor, rename, or reformat code outside the files listed here.
- Commit in small logical steps (migration → calc → db → parsing → api → chat skill → frontend → tests).
- Test the migration against a local database before the hosted one. Never write credentials into source files.

## Key decisions already made (do not re-litigate)
1. **Human-confirm before apply.** The system extracts the supplier's number and suggests the target line item, but the analyst confirms/edits/rejects before anything changes. Nothing is ever auto-applied to a footprint.
2. **Primary value = component total cradle-to-gate kg CO₂e.** The supplier reports one number that directly overrides that line item's `kg_co2e`. No activity-based EF recompute.
3. **Two entry points, one primitive.** The supplier-email loop and a manual "enter supplier value" control on the product detail page both call the same `apply_primary_data` operation.
4. **Applying primary data creates a NEW version** (Phase 2 lineage, `version = n+1`), leaving the source version immutable. Provenance is the lineage itself: version n holds the secondary value, version n+1 holds the primary value.

## The core primitive
`apply_primary_data(source_product_id, item_id, primary_kg_co2e, source_note, *, user_id, access_token) -> dict`:
read source product + its line items → clone line items → override the matched item (`kg_co2e = primary_kg_co2e`, `data_source = "primary"`, `ef_source = f"Supplier primary data: {source_note}"`, `emission_factor = NULL`) → recompute `total_kg_co2e = sum(line kg_co2e)` and every `share_pct` → compute PDS → insert a new `products` row (same `product_lineage_id`, `version = source.version + 1`, `status = "approved"`) + cloned/overridden `line_items`. Returns `{new_product_id, version, pds_before, pds_after}`.

## Do-NOT-touch list
- `parsing/`, `factors/`, `calc/footprint.py`, `calc/critic.py` — core pipeline unchanged (adding a NEW `calc/pds.py` is fine)
- `exchange/pact.py` — already reads `primary_data_share`; it starts reflecting real values automatically. No edit — only a new test asserting non-zero PDS still validates against the vendored schema.
- Existing migrations `001`–`021`; Phase 2 lifecycle/versioning logic in `db/store.py`
- `app.py`, `pages/`, `.github/workflows/`
- The dashboard/portfolio/detail page structure from Phase 2 — extend the detail page and suppliers page, do not restructure them.

## Steps

### 1. Migration — `supabase/migrations/022_engagement_primary_outcome.sql`
Add nullable columns to `engagements` (records the applied outcome, drives the "raised PDS a%→b%" UI):
```sql
ALTER TABLE engagements
    ADD COLUMN IF NOT EXISTS primary_kg_co2e      DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS applied_to_product_id BIGINT,
    ADD COLUMN IF NOT EXISTS pds_before           DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS pds_after            DOUBLE PRECISION;
```
No `line_items`/`products` schema change — `data_source` and `primary_data_share` already exist. Verify existing engagements still load afterward.

### 2. `calc/pds.py` (new — pure business logic, no DB/UI imports)
`compute_primary_data_share(line_items) -> float`: `sum(kg_co2e where data_source == "primary") / sum(all kg_co2e)`, clamped to [0,1]; returns `0.0` when total is 0 or there are no primary items. Accept line items as dicts (matching `db.reader` row shape: keys `kg_co2e`, `data_source`).

### 3. `db/store.py`
- Add `apply_primary_data(...)` (the core primitive above). Reuse the lineage/version pattern already in `save_analysis`. Import `compute_primary_data_share` from `calc.pds` (db→calc is already an allowed direction — this file imports `calc.footprint`). Read the source via `db.reader.get_product_by_id` (includes `line_items`). Raise `ValueError` if the product or `item_id` is not found.
- In `save_analysis` (normal BOM path): compute `primary_data_share` from the result's line items' `data_source` via `compute_primary_data_share` instead of relying on the hardcoded `0` default — for a fresh BOM every line is secondary so it stays `0`, but the field is now always correct rather than assumed.
- When `apply_primary_data` is called with an `engagement_id`, record `primary_kg_co2e`, `applied_to_product_id`, `pds_before`, `pds_after` on the engagement (extend `update_engagement`'s allowed-fields set in `db/copilot_store.py`).

### 4. `db/reader.py`
Add `find_line_item_for_engagement(product_name, component, material, access_token) -> dict` returning the best line-item match in the **latest-version** product row of that name (highest `version`; if names collide across lineages, most recent `created_at`): exact `(component, material)` match. Return `{product_id, version, item_id, matches: [...]}` — include all candidates when 0 or >1 exact matches so the UI can let the analyst pick. (Note: `line_items` currently isn't selected with `item_id` in `_LINE_ITEM_COLUMNS`; add `item_id` there so matches carry an id.)

### 5. Supplier response parsing — extract the candidate number
Extend `ParsedResponse` (`copilot/models.py`) with `primary_kg_co2e: float | None = None`. In `copilot/parse_response.py`, add `primary_kg_co2e` to the required JSON block and `_parse_structured` (parse to float, only meaningful when `completeness_score == "complete"`; otherwise `None`). Prompt guidance: extract the single total cradle-to-gate kg CO₂e the supplier reports for the component, or null if none/ambiguous. This is the "system extracts the number" half — it is never auto-applied.

### 6. API — `api/routes/analyzer.py`, `api/routes/copilot.py`, `api/models/schemas.py`
- New models in `schemas.py`: `ApplyPrimaryDataRequest { item_id: int, primary_kg_co2e: float, source_note: str, engagement_id: int | None = None }` (validator: `primary_kg_co2e > 0`), `ApplyPrimaryDataResponse { new_product_id: int, version: int, pds_before: float, pds_after: float }`.
- `POST /api/analyses/{product_id}/primary-data` in `analyzer.py`: calls `apply_primary_data`; 404 on missing product/item (catch `ValueError`), 422 on non-positive value; returns the response model. This is the single apply endpoint BOTH UIs use.
- In `copilot.py`'s route-response result: when routing action is `STORE_DATA`, include the extracted `parsed.primary_kg_co2e` and a suggested match from `find_line_item_for_engagement(...)` so the frontend can render the confirm card. The apply itself still goes through the primary-data endpoint (with `engagement_id`) after the analyst confirms. Extend the relevant response DTO(s).

### 7. Chat skill — `api/skills/analysis.py`
Add a `rank_secondary_hotspots` action: for a given product, return secondary-data line items ranked by `kg_co2e` descending (largest secondary contributors = highest-leverage supplier targets). Reuse existing line-item reads; mirror the existing `get_hotspots` handler shape. Add it to the `parameters_schema` enum and the handler dispatch.

### 8. Frontend
- `frontend/src/lib/api.ts`: add `applyPrimaryData(productId, { item_id, primary_kg_co2e, source_note, engagement_id? })`; extend types for the new route-response fields. `frontend/src/lib/supabase-data.ts`: add `data_source` (and `item_id` if needed) to `LINE_ITEM_COLUMNS` — **both** column lists must stay in sync (Phase 2 lesson).
- Product detail (`frontend/src/app/analyzer/[id]/page.tsx`): per-line-item primary/secondary `Badge` (from `data_source`); on a secondary line item, an "Enter supplier value" action → dialog (kg CO₂e number + source note text) → `applyPrimaryData` → on success show "Created v{version}, PDS {pds_before}→{pds_after}" (use `formatPct`, values are 0–1 fractions ×100) and link to `/analyzer/{new_product_id}`. Reuse existing dialog/`MetricCard`/`Badge` components.
- Suppliers (`frontend/src/app/suppliers/*`): after a response routes as `STORE_DATA`, render a confirm card with the extracted value + suggested line item (both editable — analyst can change the value or pick a different line item from candidates) → confirm calls `applyPrimaryData` with `engagement_id` → show the PDS improvement.

### 9. Tests
- `tests/test_pds.py`: `compute_primary_data_share` — mixed set equals `sum(primary)/total`; `0.0` with no primary; `1.0` all-primary; `0.0` on empty/zero total. This is the **eval invariant** ("PDS = primary kg ÷ total").
- `apply_primary_data` (in `tests/test_versioning.py` or a new file, matching the mocking style used there): new version created (same `product_lineage_id`, `version+1`), matched item overridden with `data_source="primary"`, total + PDS recomputed, and the **source version row is unchanged** (immutability).
- `tests/test_api.py`: `POST /api/analyses/{id}/primary-data` returns correct `pds_after` + new version; 404 for missing product/item; 422 for `primary_kg_co2e <= 0`.
- Parse: a supplier email containing a number yields `primary_kg_co2e` (extend copilot parse tests if present, else add one).
- PACT export: a product with a non-zero `primary_data_share` serializes `primaryDataShare` correctly and still validates against `tests/fixtures/pact_v3_product_footprint_schema.json`.

## Acceptance criteria
```bash
ruff check --ignore E501 evals tests calc parsing factors api llm copilot gap_analyzer rag db observability exchange
pytest tests -v
cd frontend && npm run lint && npm run build
```
Manual demo (the phase gate — product owner walks this; DEMO_SCRIPT.md Phase 3 line):
1. `uvicorn api.main:app --reload` + `cd frontend && npm run dev`
2. Open an approved product with PDS 0% → on a secondary line item, "Enter supplier value" → enter a kg CO₂e + note → confirm
3. A new version appears with that line item marked **primary**, PDS risen above 0%
4. (Supplier path) Route a supplier response that includes a number → confirm the suggested value/line item → same result, engagement records the PDS improvement
5. Export the PACT payload → `primaryDataShare` is now non-zero and the payload still validates

## Out of scope (do not build)
Activity-based recompute (supplier gives a total, not EF+activity); auto-apply without confirmation; splitting one line item across multiple suppliers; DQR/data-quality scoring beyond PDS; Phase 4 scenario modeling; unpublish/delete.
