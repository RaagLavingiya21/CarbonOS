# Phase 2 Implementation Plan — Portfolio & Footprint Lifecycle

**Executes:** Phase 2 of `PCF_PLATFORM_DESIGN.md`. Read that file and `CLAUDE.md` before starting.
**Branch:** `feature/phase-2-portfolio-lifecycle`
**Builds on:** Phase 1 (merged as PR #12, PR #13, PR for `fix/pact-decimal-scientific-notation`) — `products` already has `footprint_uuid`, `declared_unit`, `unitary_product_amount`, `system_boundary`, `reporting_period_start/end`, `geography_country`, `primary_data_share`, `spec_version`, `version` (currently unused, always 1).
**Outcome:** An analyst can see every product's footprint status and version in one portfolio view, drill from a dashboard KPI down to a single line item's source citation, publish an approved footprint, and recalculate a product to produce a new version.

## Instructions for the implementer

- Implement exactly what this plan specifies. If something is ambiguous or looks wrong, STOP and report it — do not improvise or redesign.
- Do not refactor, rename, or reformat any code outside the files listed here.
- Commit in small logical steps (migration → backend → frontend → tests).
- Never write credentials into source files. Environment variables only.

## Do-NOT-touch list

- `parsing/`, `factors/`, `calc/`, `exchange/` — core pipeline and PACT serialization logic (Phase 1's `exchange/pact.py` fix already exists on `fix/pact-decimal-scientific-notation` — merge that first if it hasn't landed; do not re-touch `_decimal_str`)
- `api/agent/`, `copilot/`, `gap_analyzer/`, `rag/`, `llm/` — other modules' logic
- `app.py`, `pages/` — legacy Streamlit
- `.github/workflows/` — CI config
- Existing migrations `001`–`020` — never edit an applied migration
- The chat-first home page hero and module showcase cards (`MODULES` array in `frontend/src/app/page.tsx`) — this phase ADDS a KPI section, it does not replace the existing chat-first design from a prior redesign phase
- `/analyzer/[id]/page.tsx`'s existing metric cards, hotspot bars, and CSV export — extend, do not rewrite

## Key decisions already made (do not re-litigate)

**Lifecycle scope is `approved → published`, not the full `draft → calculated → under_review → approved → published` chain named in the design doc.** Investigation of the current code shows the BOM analyzer is a single client-session workflow (parse → match → calculate → human review, all held in an in-memory `session_store`, per `api/routes/analyzer.py`) — no DB row exists until the analyst clicks save with a final status. Persisting `draft`/`calculated`/`under_review` as portfolio-visible rows would require a bigger rearchitecture (partial analyses visible to a whole org) that isn't needed to deliver this phase's actual jobs (portfolio visibility, lifecycle, versioning, dashboard). This plan adds exactly one new status, `published`, reachable only from `approved`. The existing `approved`/`flagged` statuses and their behavior (including Phase 1's PACT export gate: `status == "approved"`) do not change.

**Versioning uses a lineage, not in-place mutation.** A new `product_lineage_id` column groups every version of "the same product" together. The first save of a product generates a fresh lineage id; a "Recalculate" action creates a brand-new row with the same lineage id and `version = max(existing versions) + 1`. Rows are never edited in place — this is why "published versions are immutable" falls out for free: nothing ever writes to an existing row after creation except the one new `publish` action (status + `published_at`).

**`/analyzer/[id]` stays the product detail page.** The design doc's original IA sketch named `/products/{id}`; investigation found `frontend/src/app/analyzer/[id]/page.tsx` already exists, is well-built (metric cards, hotspot bars with source citations, CSV export), and is linked from elsewhere. Reuse it — extend with the new fields and actions — rather than building a duplicate route. `/products` (new) is the portfolio list; each row links to `/analyzer/{id}`.

**Two frontend data-access paths must both be updated.** `frontend/src/lib/api.ts` calls the FastAPI backend; `frontend/src/lib/supabase-data.ts` reads Supabase directly (used by `/analyzer/[id]` and the supplier copilot intake form) with its own separate `PRODUCT_COLUMNS`/`LINE_ITEM_COLUMNS` string constants. Both column lists must be extended with new fields — they are not automatically in sync.

**Audit logging reuses `append_audit_log` from `db/copilot_store.py` as-is.** Its signature (`event`, `workflow`, `user_id`, `access_token`, plus optional supplier-specific kwargs, `product_name`, `status`) already covers what's needed for lifecycle events without a schema change — call it with `workflow="footprint_lifecycle"` and leave copilot-only kwargs unset. Do not move or refactor this function.

---

## Step 1 — Database migration

**New file:** `supabase/migrations/021_footprint_lineage_and_publish.sql`

```sql
-- Versioning lineage + publish lifecycle (see PCF_PLATFORM_DESIGN.md, Phase 2)

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS product_lineage_id UUID NOT NULL DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS published_at        TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_products_lineage_id ON products (product_lineage_id);

ALTER TABLE products
    ADD CONSTRAINT products_status_check
    CHECK (status IN ('approved', 'flagged', 'published'));
```

The `DEFAULT gen_random_uuid()` means every existing row gets its own distinct lineage id (correct: each pre-Phase-2 row is version 1 of its own, previously-unversioned lineage). The `CHECK` constraint only adds `'published'` as a new allowed value — existing `'approved'`/`'flagged'` rows are unaffected.

**Migration safety (mandatory, same as Phase 1):** apply and verify against a local database before the hosted Supabase project. Confirm `GET /api/analyses` still returns existing rows unchanged afterward.

## Step 2 — Backend: versioning + publish

**Modify `db/reader.py`:**
- Add `product_lineage_id, published_at` to `_PRODUCT_COLUMNS`.
- Add an optional `status: str | None = None` keyword param to `get_all_products` and thread it through `get_products_for_active_org`; when set, filter with `.eq("status", status)`.

**Modify `db/store.py`:**
- `save_analysis(...)` gains an optional `recalculate_of_product_id: int | None = None` keyword param. When provided: look up the source row via `get_product_by_id` (import from `db.reader`), reuse its `product_lineage_id`, and set `version = source["version"] + 1`. When not provided: let the column default (`gen_random_uuid()`) handle a fresh lineage id and hardcode `version = 1`. Insert both `product_lineage_id` and `version` explicitly into the insert dict either way (don't rely on the DB default for the version number — only the lineage id has a DB-level default).
- New function `publish_analysis(product_id: int, *, user_id: str, access_token: str) -> None`: read the current row, raise `ValueError` if `status != "approved"`, else update `status="published"`, `published_at=now().isoformat()`. Call `append_audit_log(event="published", workflow="footprint_lifecycle", user_id=user_id, access_token=access_token, product_name=..., status="published")` (import from `db.copilot_store`) after the update succeeds.

**Modify `api/models/schemas.py`:**
- Add `product_lineage_id: str | None = None`, `published_at: str | None = None`, `version: int | None = None`, `primary_data_share: float | None = None`, `declared_unit: str | None = None` to `AnalysisSummaryDTO` (they auto-populate via the existing `from_row` pattern — no other change needed there).
- `SaveAnalysisRequest` gains `recalculate_of_product_id: int | None = None`.
- New `PublishAnalysisResponse(BaseModel)`: `product_id: int`, `status: str`, `published_at: str`.

**Modify `api/routes/analyzer.py`:**
- `GET /api/analyses` gains an optional `status: str | None = Query(None)` param, passed through to `get_products_for_active_org`.
- `POST /api/analyses` (existing save endpoint) and the save path inside `POST /api/analyze`: accept `recalculate_of_product_id` (Form field on `/api/analyze`, request field on `/api/analyses`) and pass it through to `save_analysis`.
- New endpoint:
```python
@router.post("/api/analyses/{product_id}/publish", response_model=PublishAnalysisResponse)
def publish_analysis_route(
    product_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> PublishAnalysisResponse:
    # 404 if get_product_by_id returns None
    # 409 if status != "approved" (catch the ValueError from publish_analysis, translate to HTTPException)
    # on success, re-fetch and return the new status + published_at
```
- New endpoint for dashboard KPIs:
```python
@router.get("/api/analyses/summary")
def get_portfolio_summary(current_user: CurrentUser = Depends(get_current_user)) -> dict:
    # reuse get_products_for_active_org (no new SQL) - compute in Python:
    # total_kg_co2e (sum), avg_primary_data_share, counts_by_status (dict), open_flags_count
    # (count of products where flagged_items > 0)
```
Place this route before `/api/analyses/{product_id}` so `"summary"` doesn't get captured by the path param — or give it a distinct path like `/api/analyses/summary` registered earlier in the file; verify with a quick manual request that FastAPI doesn't try to parse `"summary"` as an int product_id (it will 422; order matters, register `/api/analyses/summary` above the `{product_id}` route).

## Step 3 — Chat skill: portfolio queries

**Modify `api/skills/analysis.py`:** add an optional `status` parameter to the `list_products` action's parameters schema and to `_list_products`, threading it into `get_all_products`/`get_products_for_active_org` (reuse the reader change from Step 2). No new action needed — extending `list_products` covers "which products are still in draft/approved/published" per the design doc's example query.

## Step 4 — Frontend: portfolio page

**New file:** `frontend/src/app/products/page.tsx`
- Fetches `GET /api/analyses` (extend `frontend/src/lib/api.ts`'s existing analyses-list function to accept an optional `status` query param).
- Reads `?status=` from the URL search params to pre-filter (this is what makes dashboard KPIs clickable into a filtered list).
- Table columns: product name, status (badge, reuse the `Badge` component pattern already used in `/analyzer/[id]`), version, total kg CO₂e, primary data share, flagged items count.
- Each row links to `/analyzer/{product_id}`.
- Reuse existing UI primitives (`Card`, `Badge`, `Skeleton`, `ErrorState`) — match the styling already established on `/analyzer/[id]` and `/gap-analysis`.

**Modify `frontend/src/lib/api.ts`:**
- Extend `AnalysisSummary` type with `product_lineage_id?: string | null`, `published_at?: string | null`, `version?: number | null`, `primary_data_share?: number | null`, `declared_unit?: string | null`.
- Add `status` as an optional query param to the existing analyses-list function.
- New `api.publishAnalysis(productId: number): Promise<{product_id: number; status: string; published_at: string}>` calling the new publish endpoint.
- New `api.getPortfolioSummary(): Promise<PortfolioSummary>` (define the type matching Step 2's summary shape).

**Modify `frontend/src/lib/supabase-data.ts`:** add `product_lineage_id, published_at, version, primary_data_share, declared_unit` to `PRODUCT_COLUMNS` (this is the second, separate column list flagged above — required for `/analyzer/[id]` to see the new fields at all, since it reads via this path, not `api.ts`).

## Step 5 — Frontend: extend `/analyzer/[id]`

**Modify `frontend/src/app/analyzer/[id]/page.tsx`:**
- Add a fourth `MetricCard` for Primary Data Share (reuse the existing `MetricCard` component — already imported).
- Update the status `Badge` to handle `"published"` (e.g., a distinct badge variant/color from `"approved"`/`"flagged"`).
- Add a "Publish" button, visible only when `status === "approved"`, calling `api.publishAnalysis` and updating local state on success; disabled with a tooltip/label when already published ("Published — read-only").
- Add the "Export PACT payload" button + preview sheet — copy the existing pattern already implemented in `frontend/src/app/analyzer/page.tsx` (the `pactPayload` state, `fetchPactPayload` call, `Sheet` preview, copy/download actions) rather than reinventing it. This was previously only reachable right after saving; now every saved product's detail page can export it.
- Add a small "Recalculate" link/button that navigates to `/analyzer?recalculate_of={product_id}&product_name={encoded name}` (a new optional query-param read on the analyzer upload page, Step 6).

## Step 6 — Frontend: recalculate entry point

**Modify `frontend/src/app/analyzer/page.tsx`:**
- On mount, read `recalculate_of` and `product_name` from the URL search params if present; pre-fill the product name field and store the `recalculate_of` id in state.
- When saving, include `recalculate_of_product_id` in the save request if set.
- After a successful save from a recalculation, the success view should note "This is version N of {product_name}."

## Step 7 — Dashboard KPI section

**Modify `frontend/src/app/page.tsx`:**
- Add a new section between the hero/chat-input and the existing `MODULES` showcase (do not remove or reorder the existing showcase).
- Fetch `api.getPortfolioSummary()` on mount alongside the existing recent-threads fetch.
- Render KPI cards (reuse `MetricCard`): total portfolio kg CO₂e, average primary data share, open flags count, and one card per status with a count — each card is a `Link` to `/products?status=X` (the open-flags card can link to `/products` unfiltered, or add a `flagged_items_gt=0`-style filter if trivial; if not trivial, link to `/products` and note the limitation rather than over-building the filter).
- Empty state: if the user has zero saved products, show a lightweight prompt instead of zeroed-out KPI cards.

---

## Step 8 — Tests

**New file `tests/test_versioning.py`** (or extend `tests/test_api.py` if that fits the existing test style better — check the file before deciding):
1. Saving with `recalculate_of_product_id` set produces a new row with the same `product_lineage_id` and `version = source.version + 1`.
2. Saving without it produces `version = 1` and a fresh lineage id different from any other product's.
3. `publish_analysis` succeeds from `"approved"` and sets `published_at`.
4. `publish_analysis` raises/rejects when called on a `"flagged"` or already-`"published"` row.
5. `GET /api/analyses?status=published` returns only published rows (mock at whatever layer the existing `test_api.py` tests mock at — follow that pattern).
6. `POST /api/analyses/{id}/publish` returns 409 for a non-approved product, 404 for a missing one (mirror the style of the existing `test_export_pact_returns_409_for_flagged_product` test).
7. `GET /api/analyses/summary` returns correct aggregate counts for a small fixture set of products across statuses.

## Acceptance criteria (all must pass)

```bash
ruff check --ignore E501 evals tests calc parsing factors api llm copilot gap_analyzer rag db observability exchange
pytest tests -v
cd frontend && npm run lint && npm run build
```

Manual demo script (the phase gate — product owner walks this, per `DEMO_SCRIPT.md` beat 5):
1. `uvicorn api.main:app` + `cd frontend && npm run dev`
2. Dashboard shows portfolio KPI cards with real totals
3. Click a KPI → land on `/products` filtered to that status
4. Click a product row → land on `/analyzer/{id}` → see version, PDS, status
5. Click Publish on an approved product → status flips, published_at appears, button becomes disabled
6. Click Recalculate → land back on the analyzer upload flow pre-filled → save → new row appears in `/products` as version 2 of the same product

## Out of scope for this phase (do not build)

`draft`/`calculated`/`under_review` as persisted statuses, primary-data-driven PDS changes (Phase 3), scenario modeling (Phase 4), any UI for browsing a lineage's full version history beyond "latest version" (a "version history" list view is a reasonable Phase 2 stretch but not required for the demo script — only build it if Steps 1–7 are done and tested with time remaining), unpublishing/deleting published rows.
