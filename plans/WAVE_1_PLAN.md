# Wave 1 Implementation Plan — "Make the Trust Real"

**Executes:** Wave 1 of `PRODUCT_STRATEGY.md` — DQR + provenance + portfolio health + maker-checker. Read `PRODUCT_STRATEGY.md`, `PCF_PLATFORM_DESIGN.md`, and `CLAUDE.md` before starting.
**Branch:** `feature/wave-1-trust` (created off `main`, which has Phases 1–4 merged).
**Size:** large — four independent workstreams (A–D). Commit each workstream separately. Splitting into sequential PRs (A → B+C → D) is encouraged to keep each review tractable.

## Why
The product's core promise is "auditable / standards-grade," but two things make that partly untrue today: the PACT export's **DQR is hardcoded `"4"/"4"/"4"`** in `exchange/pact.py`, and there's **no second-person review** before publish (Phase 2 dropped `under_review`). Wave 1 closes the gaps where the product contradicts its own promise before adding new surface area.

## Instructions for the implementer
- Implement exactly what this plan specifies. If something is ambiguous or looks wrong, STOP and report it — do not improvise or redesign.
- Do not modify code outside the files named per workstream. Commit in small logical steps.
- Test every migration on a local DB first. Never write credentials into source files.
- Recommended order: **A (DQR) → B (provenance, consumes DQR) → C (portfolio health, reuses DQR) → D (maker-checker, independent)**.
- New pure modules (`calc/dqr.py`, `calc/health.py`) mirror `calc/pds.py` — no DB/UI imports.

## Do-NOT-touch
- `parsing/`, `factors/ef_lookup.py`, `calc/footprint.py`, `calc/critic.py`, `calc/pds.py` (call/read, don't modify)
- `db/scenario_store.py` and the scenario tables (Phase 4) — out of scope for DQR
- Existing migrations `001`–`023`; the Phase 1–4 PACT/lineage/PDS/scenario logic except the specific edits named below
- `app.py`, `pages/`, `.github/workflows/`

---

## Workstream A — Real DQR (Data Quality Rating)

**Goal:** replace the hardcoded `4/4/4` with a computed technological / geographical / temporal DQR (1 = best … 5 = worst, PACT convention), per line item and aggregated per footprint, feeding both the PACT export and a UI surface.

**A1. Migration `supabase/migrations/024_line_item_dqr_signals.sql`** — persist the signals `calc/footprint.LineItem` already computes but `db/store.py._line_item_row` currently drops. Add to `line_items` (all nullable): `ef_confidence DOUBLE PRECISION`, `country_of_origin TEXT`, `technological_dqr SMALLINT`, `geographical_dqr SMALLINT`, `temporal_dqr SMALLINT`. Add to `products`: `technological_dqr SMALLINT`, `geographical_dqr SMALLINT`, `temporal_dqr SMALLINT`, `dqr_computed_at TIMESTAMPTZ`.

**A2. `calc/dqr.py` (new, pure)** —
- `CEDA_VINTAGE_YEAR = 2025` module constant.
- `line_item_dqr(*, ef_confidence, is_low_confidence, data_source, country_of_origin, reporting_year) -> dict[str,int]` → `{"technological", "geographical", "temporal"}` on 1–5. Documented rules: **technological** = 1 if `data_source == "primary"`, else by `ef_confidence` bands (≥90→2, ≥75→3, ≥60→4, else 5); **geographical** = 2 if a specific `country_of_origin` is set, else 4 (global/USA fallback); **temporal** by `abs(reporting_year - CEDA_VINTAGE_YEAR)` (≤1→1, ≤3→2, ≤5→3, else 4).
- `aggregate_dqr(line_items: list[dict]) -> dict[str,int]` = kg_co2e-weighted mean per dimension over matched lines (simple mean if total 0), rounded to nearest int. Line items are dicts carrying `kg_co2e` + the three per-line dqr values.

**A3. Persist at write time (`db/store.py`)** — in `_line_item_row`, also write `ef_confidence` (from `LineItem.ef_confidence`), `country_of_origin` (from `LineItem.country_of_origin`), and the three per-line DQR values via `calc.dqr.line_item_dqr` (derive `reporting_year` from the product's `reporting_period_start`). In `save_analysis` and `apply_primary_data`, compute + store the product-level aggregate DQR (via `aggregate_dqr`) and `dqr_computed_at`. In `apply_primary_data`, the overridden primary line gets `data_source="primary"` → technological DQR 1 (falls out of the same helper — just pass the row's fields through it). Do **not** touch `db/scenario_store.py`.

**A4. PACT export (`exchange/pact.py`)** — replace the literal `"dqi": {"technologicalDQR":"4", ...}` block with the product's stored aggregate DQR values as decimal strings. Keep validation + decimals-as-strings behavior intact. Update `db/reader.py` `_PRODUCT_COLUMNS` and `_LINE_ITEM_COLUMNS` to select the new columns.

**A5. UI (`frontend/src/app/analyzer/[id]/page.tsx`)** — a "Data quality" section: the three aggregate DQR scores with a one-line legend (1 = best … 5 = worst) and a per-line DQR indicator in the line-item table. Update `frontend/src/lib/api.ts` types and **both** `frontend/src/lib/supabase-data.ts` column lists (Phase 2 lesson).

**A6. Tests `tests/test_dqr.py`** — band rules; `data_source="primary"` → technological 1; aggregate weighting; **eval invariant**: PACT `dqi` equals the computed aggregate (assert it is NOT hardcoded 4 for a non-trivial product); PACT payload still validates against `tests/fixtures/pact_v3_product_footprint_schema.json` with computed DQR.

---

## Workstream B — Footprint provenance / methodology view

**Goal:** a consolidated, auditor-facing "how every number was derived" view + export per footprint.

**B1. Backend (`db/reader.py` + `api/routes/analyzer.py`)** — `get_footprint_provenance(product_id, access_token) -> dict` reusing `get_product_by_id` + a lineage query over `product_lineage_id`: product metadata (declared unit, boundary, geography, reporting period), method statement (spend-based Open CEDA 2025, cradle-to-gate screening), PDS, aggregate DQR, per-line records (material → matched sector, EF, `ef_source` citation, `ef_confidence`, `data_source`, per-line DQR), and the version lineage (all versions with dates/status). Endpoint `GET /api/footprints/{product_id}/provenance` returns JSON; `?format=markdown` returns a human-readable methodology statement (pure string builder in a small helper, e.g. `exchange/provenance.py` or inline — no PDF deps). 404 for missing product.

**B2. UI** — a "Provenance / methodology" section or tab on the detail page rendering the object, with "Download methodology (.md / .json)" buttons (reuse the download pattern from the existing PACT export sheet). New `api.ts` call `fetchProvenance(productId, format?)`.

**B3. Tests** — provenance object contains every matched line's citation + per-line DQR + the version list; markdown builder returns non-empty text containing the method statement; endpoint 404s for a missing product.

---

## Workstream C — Portfolio health (staleness / needs-attention)

**Goal:** at a glance, which footprints need attention — no background jobs (scope to computable-from-stored-state signals).

**C1. `calc/health.py` (new, pure)** — `footprint_health(product: dict) -> dict` → `{"status": "healthy"|"attention"|"stale", "reasons": [...]}`. Rules (documented): **stale** if the reporting-period end year < current year; **attention** if `status == "flagged"`, `primary_data_share == 0`, aggregate DQR ≥ 4 (any dimension or the mean — pick and document), or `flagged_items > 0`; else **healthy**.

**C2. Backend (`api/routes/analyzer.py`)** — extend `GET /api/analyses/summary` and `GET /api/analyses` to include each product's health via `calc.health.footprint_health` (and a health-count breakdown in the summary). No new tables.

**C3. UI** — on `/products`: a health badge column + a "Needs attention" filter (reuse the `?status=` filter pattern with a `health=` param). On the dashboard: a "Needs attention" KPI card linking into the filtered portfolio (reuse the Phase 2 KPI drill-down). Update types + both column lists.

**C4. Tests** — health rules (stale by reporting year; attention by flags/PDS/DQR; healthy otherwise); summary endpoint returns health counts.

---

## Workstream D — Maker-checker (review before publish)

**Goal:** no one can solo-publish; a footprint must be reviewed and published by a **different** org member. Restores `under_review`.

**D1. Migration `supabase/migrations/025_review_lifecycle.sql`** — drop and recreate the `products` status CHECK (from migration 021) to allow `('approved','flagged','under_review','published')`. Add nullable `submitted_for_review_by UUID`, `submitted_at TIMESTAMPTZ`, `reviewed_by UUID`, `reviewed_at TIMESTAMPTZ`, `review_comment TEXT`.

**D2. Backend (`db/store.py` + `api/routes/analyzer.py`)** —
- `submit_for_review(product_id, *, user_id, access_token)`: `approved → under_review`; set `submitted_for_review_by`/`submitted_at`; `append_audit_log(event="submitted_for_review", workflow="footprint_lifecycle", ...)`.
- `approve_review(product_id, *, reviewer_user_id, access_token)`: require status `under_review` **and** `reviewer_user_id != submitted_for_review_by` (raise `ValueError` → 409 "review requires a different approver") **and** reviewer is an org member (reuse `db/org_store.get_active_org_member_ids`); set `reviewed_by`/`reviewed_at`, `status="published"`, `published_at`; audit-log.
- `reject_review(product_id, comment, *, reviewer_user_id, access_token)`: `under_review → flagged`, set `review_comment`; audit-log.
- **Change the publish gate**: a footprint now reaches `published` **only** via `approve_review`. Update the existing Phase 2 publish route/`publish_analysis` so there is **no solo-publish backdoor** — either remove the direct-publish endpoint or repoint it to require review. Endpoints: `POST /api/analyses/{id}/submit-review`, `POST /api/analyses/{id}/approve-review`, `POST /api/analyses/{id}/reject-review`.

**D3. UI (`frontend/src/app/analyzer/[id]/page.tsx` + `/products`)** — "Submit for review" on an `approved` footprint; on `under_review`, a review panel with Approve / Reject, **disabled for the submitter** with an explanatory tooltip; show submitter/reviewer + timestamps in the lifecycle section. A review queue = `?status=under_review` filter on `/products` (dedicated page optional). Replace the old solo "Publish" affordance.

**D4. Tests** — `submit_for_review` transition; `approve_review` by the **same** user → 409; by a **different** member → published with `reviewed_by` recorded; `reject_review` → flagged with comment; **eval invariant**: a published footprint always has `reviewed_by != submitted_for_review_by`. Update the existing Phase 2 publish tests to the new gate.

---

## Acceptance criteria (whole plan)
```bash
ruff check --ignore E501 evals tests calc parsing factors api llm copilot gap_analyzer rag db observability exchange
pytest tests -v
cd frontend && npm run lint && npm run build
```
Manual demo: open a footprint → **Data quality** shows real computed DQR (not 4/4/4), per line → open **Provenance**, download the methodology statement → **Submit for review**, then approve as a *different* member (confirm the submitter can't approve) → it publishes → **Portfolio** shows health badges and a "Needs attention" filter → export the PACT payload and confirm `dqi` now carries the computed values.

## Out of scope (Wave 1)
Input-drift monitoring / scheduled recompute (needs a background job — defer); role-based approver gating beyond "different member"; PDF provenance export; scenario DQR; anything in Waves 2–3 (PACT network, corporate roll-up).

## Review lens (post-implementation)
Hunt "mocks-pass-but-production-breaks": a new column not selected in a read query; the `025` CHECK-constraint recreation dropping the wrong prior constraint; the maker-checker approver check missing org scoping; DQR persisted at write but not read back.
