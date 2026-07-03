# Wave 3 Implementation Plan — Corporate Scope 3 Roll-up ("Connect to Why")

**Executes:** Wave 3 of `PRODUCT_STRATEGY.md` (final roadmap item). Read `PRODUCT_STRATEGY.md`, `PCF_PLATFORM_DESIGN.md`, and `CLAUDE.md` first.
**Branch:** `feature/wave-3-rollup` (created off `main`, which has Phases 1–4 + Waves 1–2 merged).

## Why
The analyst has built per-product footprints. This wave multiplies each by how many units were made/sold and sums them into the company's **Scope 3 Category 1** (Purchased Goods) number — the figure that justifies the whole exercise and feeds ESG disclosure. It reframes the product from "makes product footprints" to "the product-level foundation of the corporate carbon report," serving the sustainability lead above the analyst. Every corporate number still drills down to a published footprint and its sources.

## Instructions for the implementer
- Implement exactly what this plan says. If something is ambiguous or looks wrong, STOP and report — do not improvise.
- Commit in small logical steps (migration → calc → db → api → frontend → tests). Test the migration on a local DB first. Never write credentials into source files.

## Locked decisions
1. **Volume is stored per product-lineage, per year** in its own table — NOT a column on the footprint. Keeps published footprints immutable (volume is business metadata, not calculated footprint data), supports year-over-year, and avoids re-entry on recalculation.
2. **Only the latest published version per lineage counts** (avoids double-counting recalculated products; ties to Wave 1 maker-checker).
3. **View = one Scope 3 Cat 1 total + per-product breakdown** for a chosen reporting year. Our footprints are all Cat 1 (cradle-to-gate purchased goods).
4. Engine unchanged (spend-based). This is a **view/aggregation, not a regulatory filing** (standing non-goal).

## Do-NOT-touch
- `parsing/`, `factors/`, `calc/footprint.py`, `calc/critic.py`, `calc/pds.py`, `calc/dqr.py`, `calc/health.py` (call/read only; new `calc/rollup.py` is fine)
- `exchange/`, `db/share_store.py`, `db/request_store.py` (Wave 2) — untouched
- `products`/`line_items` schema and footprint immutability — volume lives in a **new** table, don't add volume to `products`
- Existing migrations `001`–`027`; `app.py`, `pages/`, `.github/workflows/`

## Steps

### 1. Migration `supabase/migrations/028_product_volumes.sql`
```sql
CREATE TABLE IF NOT EXISTS product_volumes (
    volume_id           BIGSERIAL PRIMARY KEY,
    product_lineage_id  UUID NOT NULL,
    user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    year                INTEGER NOT NULL,
    annual_volume       DOUBLE PRECISION NOT NULL,
    unit                TEXT NOT NULL DEFAULT 'units',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (product_lineage_id, year)
);
CREATE INDEX IF NOT EXISTS idx_product_volumes_lineage ON product_volumes (product_lineage_id);
CREATE INDEX IF NOT EXISTS idx_product_volumes_user ON product_volumes (user_id);
```
Enable **RLS** with owner/org policies mirroring `products` (a member of the owning org can read; owner writes). Validate `annual_volume >= 0` in a CHECK or in code.

### 2. `calc/rollup.py` (new, pure — no DB/UI imports)
`compute_rollup(entries: list[dict]) -> dict`: each entry `{product_id, product_name, per_unit_kg_co2e, annual_volume}`. Returns:
```
{
  "scope3_cat1_total_kg_co2e": Σ(per_unit × volume),
  "product_count": <counted>,
  "breakdown": [ {product_id, product_name, per_unit_kg_co2e, annual_volume,
                  contribution_kg_co2e, share_pct}, ... ]  # sorted desc by contribution
}
```
Skip entries with no volume from the total (they're reported separately by the caller). Guard divide-by-zero for share_pct when total is 0.

### 3. `db/rollup_store.py` (new)
- `set_product_volume(product_id, *, year, annual_volume, unit, user_id, access_token) -> dict`: resolve the product's `product_lineage_id` via `db.reader.get_product_by_id`; **upsert** into `product_volumes` on `(product_lineage_id, year)`; return the row. (Volume is settable regardless of footprint status — it is metadata, not the immutable footprint.)
- `get_rollup(year, *, access_token, user_id) -> dict`: fetch the org's **published** products (reuse `db.reader.get_products_for_active_org(..., status="published")`), reduce to the **latest version per `product_lineage_id`** in Python (like the portfolio summary reduction), filter to footprints whose reporting-period year == `year`, look up each lineage's volume for that year, build entries, call `calc.rollup.compute_rollup`. Also return `products_missing_volume: [{product_id, product_name}]` for counted footprints with no volume that year, so the UI can flag the total as incomplete. Never treat a missing volume as zero silently.

### 4. API (`api/routes/analyzer.py` or a new `api/routes/rollup.py`, registered in `api/main.py`) + models in `schemas.py`
- `GET /api/rollup?year=YYYY` → the corporate view (org-scoped, `Depends(get_current_user)`); default year = current year if omitted.
- `PUT /api/analyses/{product_id}/volume` → body `{year, annual_volume, unit?}`; 422 if `annual_volume < 0`; 404 if product missing. Returns the saved volume.

### 5. Frontend
- New page `frontend/src/app/rollup/page.tsx` ("Corporate footprint"): a **year selector**, the headline **Scope 3 Cat 1 total** (reuse `MetricCard`), a per-product **breakdown table** (product → per-unit → annual volume → contribution → share, each row linking to `/analyzer/{product_id}`), a **"missing volume"** callout listing published products without a volume for the year, and **CSV/JSON export** (reuse the existing download pattern). Add a sidebar + ⌘K nav entry ("Corporate footprint") per the Wave-1/Wave-2 nav pattern (`app-shell.tsx`, `CommandMenu.tsx`).
- On the product detail page (`analyzer/[id]/page.tsx`): an **"Annual volume"** input (year + number + unit) that `PUT`s the volume and confirms; show the currently-stored volume for the current year.
- `frontend/src/lib/api.ts`: `fetchRollup(year)` + `setProductVolume(productId, {year, annualVolume, unit})` + types.

### 6. Tests (`tests/test_rollup.py`)
- `compute_rollup`: total == Σ(per_unit × volume); breakdown shares sum to ~100; sorted by contribution; entries without volume excluded from the total.
- `get_rollup` selection (mock the client like `tests/test_versioning.py`): picks the **latest published version per lineage**, ignores older versions, drafts/approved-not-published, and other years; `products_missing_volume` populated correctly.
- API: `GET /api/rollup?year=` returns the right total; `PUT .../volume` upserts (create then update same year) and 422s on negative volume; org scoping holds.
- **Eval invariant:** corporate total == Σ(per-unit × volume) over exactly the counted (latest-published, in-year, has-volume) products; every breakdown row corresponds to a published footprint.

## Acceptance criteria
```bash
ruff check --ignore E501 evals tests calc parsing factors api llm copilot gap_analyzer rag db observability exchange
pytest tests -v
cd frontend && npm run lint && npm run build
```
Manual demo: set annual volumes on two published products → open **Corporate footprint**, pick the year → see the Scope 3 Cat 1 total and the per-product breakdown → click a row into its footprint → a published product with no volume shows in the "missing volume" callout (not silently zero) → export the roll-up.

## Out of scope (Wave 3)
Other Scope 3 categories (all our footprints are Cat 1 — faking empty categories undercuts trust); actual CSRD/regulatory filing formats (a view is not a filing); Scope 1/2; automated volume import from ERP; multi-year trend charts.

## Review lens (post-implementation)
The double-counting guard (exactly one latest-published version per lineage), the missing-volume path (never silently zero), org scoping on both endpoints, and the usual "mocks-pass-but-production-breaks" (RLS on `product_volumes`, a column not selected, the year filter off-by-one on reporting period).
