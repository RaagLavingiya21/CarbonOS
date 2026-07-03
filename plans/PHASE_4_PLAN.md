# Phase 4 Implementation Plan — Scenario Modeling ("Reduce")

**Executes:** Phase 4 (final) of `PCF_PLATFORM_DESIGN.md`. Read that file and `CLAUDE.md` before starting.
**Branch:** `feature/phase-4-scenario-modeling` (already created off `main`, which has Phases 1–3 merged).
**Outcome:** An analyst duplicates an approved footprint as an editable **scenario**, swaps a hotspot material and/or edits spend on line items, and sees the projected footprint delta side-by-side vs the baseline — turning the tool from measurement into decision-making (the "Reduce" job).

## Instructions for the implementer
- Implement exactly what this plan specifies. If something is ambiguous or looks wrong, STOP and report it — do not improvise or redesign.
- Do not refactor, rename, or reformat code outside the files listed here.
- Commit in small logical steps (migration → db → api → chat skill → frontend → tests).
- Test the migration against a local database before the hosted one. Never write credentials into source files.

## Key decisions already made (do not re-litigate)
1. **Separate scenario tables** — `scenarios` + `scenario_line_items`, fully distinct from `products`/`line_items`. Scenarios are saveable/revisitable and **non-publishable by construction** — they physically never enter the portfolio/PDS/PACT queries. Do NOT add an `is_scenario` flag to `products` (that would force auditing every existing query).
2. **Editable: material + spend** — swap a line item's material (re-run EF matching via `factors/ef_lookup.lookup_ef` for a new factor) and/or edit `spend_usd`. Both recompute `kg_co2e = spend_usd × ef`.
3. **Promotion is out of scope** — a scenario cannot become a real footprint version this phase. Model + compare only.
4. **Engine stays spend-based (Open CEDA).** No activity-based recompute.

## Do-NOT-touch list
- `parsing/`, `factors/ef_lookup.py` (call `lookup_ef`, don't modify), `calc/footprint.py`, `calc/critic.py`, `calc/pds.py`, `exchange/pact.py`
- `products` / `line_items` tables and existing queries over them (`db/reader.py`, `db/store.py`, `db/scenario` is NEW) — scenarios are a **separate** entity; do not add columns to or alter these
- Existing migrations `001`–`022`; Phase 1–3 lifecycle/versioning/PDS logic
- `app.py`, `pages/`, `.github/workflows/`
- Portfolio/Dashboard/detail Phase 2–3 structure — extend the detail page and add a new compare page; do not restructure existing pages.

## Steps

### 1. Migration — `supabase/migrations/023_scenarios.sql`
```sql
CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id            BIGSERIAL PRIMARY KEY,
    user_id                UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    baseline_product_id    BIGINT NOT NULL,
    name                   TEXT NOT NULL,
    baseline_total_kg_co2e DOUBLE PRECISION NOT NULL,
    total_kg_co2e          DOUBLE PRECISION NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS scenario_line_items (
    scenario_item_id  BIGSERIAL PRIMARY KEY,
    scenario_id       BIGINT NOT NULL REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    user_id           UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    component         TEXT,
    material          TEXT,
    spend_usd         DOUBLE PRECISION,
    matched_sector    TEXT,
    emission_factor   DOUBLE PRECISION,
    ef_source         TEXT,
    kg_co2e           DOUBLE PRECISION,
    share_pct         DOUBLE PRECISION,
    baseline_material TEXT,
    baseline_kg_co2e  DOUBLE PRECISION,
    is_edited         BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_scenarios_user_id ON scenarios (user_id);
CREATE INDEX IF NOT EXISTS idx_scenarios_baseline ON scenarios (baseline_product_id);
CREATE INDEX IF NOT EXISTS idx_scenario_items_scenario ON scenario_line_items (scenario_id);
CREATE INDEX IF NOT EXISTS idx_scenario_items_user ON scenario_line_items (user_id);
```
**Add RLS**: enable row-level security on both tables with user-scoped policies (SELECT/INSERT/UPDATE/DELETE where `user_id = auth.uid()`), mirroring the existing pattern in migration `004_enable_rls.sql` for `products`/`line_items`. Missing RLS would make scenario reads/writes 403 at runtime even though mocked tests pass — verify a real create+read round-trips before moving on.

### 2. `db/scenario_store.py` (new — mirror the patterns in `db/store.py` and `db/reader.py`; use `get_user_client(access_token)`)
- `create_scenario_from_product(baseline_product_id, name, *, user_id, access_token) -> int`: read baseline via `db.reader.get_product_by_id`; clone its line items into `scenario_line_items` with `baseline_material = material`, `baseline_kg_co2e = kg_co2e`, `is_edited = false`; store `baseline_total_kg_co2e` and `total_kg_co2e` (equal at creation).
- `edit_scenario_line_item(scenario_item_id, *, material=None, spend_usd=None, user_id, access_token) -> dict`: load the item; if `material` changed, call `lookup_ef(material, None)` → set `emission_factor = match.ef_kg_co2e_per_usd`, `matched_sector`, `ef_source` (from the `EFMatch`); recompute `kg_co2e = (spend_usd if given else current spend) × emission_factor`; set `is_edited = true`; then recompute the scenario's `total_kg_co2e` and every item's `share_pct`; persist and return `{scenario_total, baseline_total, delta_kg, delta_pct, item}`. Reuse the exact `spend × ef` formula from `calc/footprint.py` (do not invent a new one).
- `get_scenario(scenario_id, access_token) -> dict` (scenario + its line items), `list_scenarios_for_product(baseline_product_id, access_token)`, `delete_scenario(scenario_id, *, user_id, access_token)`.
- Never write to `products`/`line_items`.

### 3. API — new router `api/routes/scenarios.py` (register in `api/main.py`) + models in `api/models/schemas.py`
- `POST /api/products/{product_id}/scenarios` — body `{ name }` → creates from baseline; 404 if product missing.
- `GET /api/scenarios/{scenario_id}` — scenario + line items + baseline totals (for the compare view); 404 if missing.
- `PATCH /api/scenarios/{scenario_id}/line-items/{scenario_item_id}` — body `{ material?, spend_usd? }` → recomputed line + new scenario total + deltas; 404 missing; 422 if `spend_usd < 0`.
- `GET /api/products/{product_id}/scenarios` (list), `DELETE /api/scenarios/{scenario_id}`.
- All endpoints `Depends(get_current_user)` and pass `access_token` through, like the other routers.

### 4. Chat skill — `api/skills/analysis.py`
Add a `create_scenario` action: given a product (name/id) and a requested change ("model X with recycled aluminium"), resolve the product, create a scenario, apply the material swap on the best-matching line item (reuse the Phase 3 `find_line_item_for_engagement`-style matching in `db/reader.py`), and return the projected delta. Add it to `parameters_schema` and the handler dispatch, mirroring the existing action shape.

### 5. Frontend
- `frontend/src/lib/api.ts`: scenario CRUD + line-item edit calls (+ TS types).
- Product detail (`frontend/src/app/analyzer/[id]/page.tsx`): a **"Model a scenario"** button → `POST .../scenarios` → route to the compare view; also list existing scenarios for this product (via `GET /api/products/{id}/scenarios`).
- New compare page `frontend/src/app/scenarios/[id]/page.tsx`: baseline vs scenario **side-by-side** — a headline total delta (e.g. "−18% vs baseline", use `formatPct`) + a per-line-item table where material (input/select) and `spend_usd` are editable; each row shows its delta vs baseline and its EF **source citation** (traceability invariant). Edited rows visibly flagged (`is_edited`). Reuse `MetricCard`, `HotspotBar`, `Badge`, and existing dialog/input components.
- Do **not** surface scenarios in Portfolio or Dashboard KPIs — they are not real footprints.

### 6. Tests (`tests/test_scenarios.py`; mock the Supabase client the way `tests/test_versioning.py` does)
- `create_scenario_from_product` clones baseline line items correctly and sets `total == baseline_total` at creation.
- `edit_scenario_line_item`: a material swap re-matches EF (`lookup_ef`) and recomputes `kg_co2e = spend × ef`; a spend edit recomputes with the existing EF; scenario `total_kg_co2e` and `share_pct` update; **eval invariant**: scenario `total_kg_co2e == sum(line kg_co2e)`; every edited line still has a non-empty `ef_source`.
- **Immutability**: editing a scenario never mutates the baseline `products`/`line_items` rows.
- API: create → edit → get returns correct `delta_kg`/`delta_pct`; 404 (missing product/scenario/item) and 422 (`spend_usd < 0`) paths.
- Chat skill: `create_scenario` produces a scenario with the requested swap applied.

## Acceptance criteria
```bash
ruff check --ignore E501 evals tests calc parsing factors api llm copilot gap_analyzer rag db observability exchange
pytest tests -v
cd frontend && npm run lint && npm run build
```
Manual demo (DEMO_SCRIPT.md Phase 4 line): open an approved product → "Model a scenario" → swap the top hotspot's material (or cut its spend) → the compare view shows the recomputed total and a clear delta vs baseline, with per-line deltas → confirm the **baseline product is unchanged**.

## Out of scope (do not build)
Promoting a scenario to a real version; supplier swaps; activity-based recompute; comparing >2 scenarios at once; scenarios in portfolio/PDS/PACT; Monte Carlo / sensitivity ranges.

## Review lens (for the post-implementation check)
Hunt "mocks-pass-but-production-breaks" gaps: a column not selected in a read query; **RLS policies missing so scenario reads/writes 403 at runtime**; a query that forgets `user_id` scoping; the `spend × ef` recompute diverging from `calc/footprint.py`.
