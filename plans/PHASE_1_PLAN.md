# Phase 1 Implementation Plan — PACT-Aligned Data Foundation + Export

**Executes:** Phase 1 of `PCF_PLATFORM_DESIGN.md`. Read that file and `CLAUDE.md` before starting.
**Branch:** `feature/phase-1-pact-foundation`
**Outcome:** A saved, approved analysis can be exported as a WBCSD PACT v3 `ProductFootprint` JSON payload that validates against the official PACT v3 JSON schema.

## Instructions for the implementer

- Implement exactly what this plan specifies. If something is ambiguous or looks wrong, STOP and report it — do not improvise or redesign.
- Do not refactor, rename, or reformat any code outside the files listed here.
- Commit in small logical steps (migration → module → endpoint → frontend → tests).
- Never write credentials into source files. Environment variables only.

## Do-NOT-touch list

- `parsing/`, `factors/`, `calc/` — core pipeline logic (you will only *read* their outputs)
- `api/agent/`, `copilot/`, `gap_analyzer/`, `rag/`, `llm/` — other modules' logic
- `app.py`, `pages/` — legacy Streamlit
- `.github/workflows/` — CI config
- Existing migrations `001`–`019` — never edit an applied migration
- Frontend routes other than `frontend/src/app/analyzer/` and `frontend/src/lib/api.ts`

---

## Step 1 — Database migration

**New file:** `supabase/migrations/020_pact_footprint_fields.sql`

```sql
-- PACT v3-aligned footprint fields (see PCF_PLATFORM_DESIGN.md §7)

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS footprint_uuid          UUID NOT NULL DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS product_description     TEXT,
    ADD COLUMN IF NOT EXISTS declared_unit           TEXT NOT NULL DEFAULT 'piece',
    ADD COLUMN IF NOT EXISTS unitary_product_amount  DOUBLE PRECISION NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS system_boundary         TEXT NOT NULL DEFAULT 'cradle-to-gate',
    ADD COLUMN IF NOT EXISTS reporting_period_start  DATE,
    ADD COLUMN IF NOT EXISTS reporting_period_end    DATE,
    ADD COLUMN IF NOT EXISTS geography_country       TEXT,
    ADD COLUMN IF NOT EXISTS primary_data_share      DOUBLE PRECISION NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS spec_version            TEXT NOT NULL DEFAULT '3.0.0',
    ADD COLUMN IF NOT EXISTS version                 INTEGER NOT NULL DEFAULT 1;

CREATE UNIQUE INDEX IF NOT EXISTS idx_products_footprint_uuid ON products (footprint_uuid);

ALTER TABLE line_items
    ADD COLUMN IF NOT EXISTS data_source TEXT NOT NULL DEFAULT 'secondary'
        CHECK (data_source IN ('primary', 'secondary'));
```

Defaults intentionally backfill existing rows (existing analyses become v1, spend-based, PDS 0%).

**Migration safety (mandatory):** apply and verify against a local database (`supabase db reset` or psql against a local Postgres with migrations 001–020) BEFORE applying to the hosted Supabase project. Confirm existing saved analyses still load via `GET /api/analyses` afterward.

## Step 2 — New business-logic module: `exchange/`

**New files:** `exchange/__init__.py`, `exchange/pact.py`

Rules: pure Python. No FastAPI, Streamlit, or HTTP imports. May import from `db/`. This module joins the business-logic list in CLAUDE.md's dependency rules (add `exchange/` to that list — one-line CLAUDE.md edit, allowed).

`exchange/pact.py` provides:

```python
def build_product_footprint(product: dict, org_name: str | None, org_id: str | None) -> dict:
    """Map a product row (incl. line_items) to a PACT v3 ProductFootprint dict."""

def validate_product_footprint(payload: dict) -> list[str]:
    """Return a list of violations (empty = valid). Checks mandatory fields,
    decimal-as-string formatting, and geography mutual exclusivity."""
```

Mapping (design doc §7):

| Payload field | Source |
|---|---|
| `id` | `footprint_uuid` |
| `specVersion` | `spec_version` |
| `version` | `version` |
| `created` / `updated` | `created_at` / `updated_at` (ISO 8601 UTC) |
| `status` | `"Active"` (PACT enum, not our lifecycle status) |
| `companyName` | active org name, else `"Independent Analyst (CarbonOS)"` |
| `companyIds` | `["urn:pfa:company:{org_id or user_id}"]` |
| `productIds` | `["urn:pfa:product:{product_id}"]` |
| `productDescription` | `product_description`, else `product_name` |
| `productNameCompany` | `product_name` |
| `pcf.declaredUnit` | `declared_unit` |
| `pcf.unitaryProductAmount` | `unitary_product_amount` as **string** |
| `pcf.pCfExcludingBiogenic` / `fossilGhgEmissions` | `total_kg_co2e / unitary_product_amount` as **string** |
| `pcf.fossilCarbonContent`, `pcf.biogenicCarbonContent` | `"0"` (spend-based method cannot resolve; document in comment) |
| `pcf.characterizationFactors` | `"AR6"` |
| `pcf.crossSectoralStandardsUsed` | `["GHG Protocol Product standard"]` |
| `pcf.boundaryProcessesDescription` | `system_boundary` + note: spend-based EEIO (Open CEDA 2025) |
| `pcf.referencePeriodStart/End` (or `reportingPeriod*` per schema) | `reporting_period_start/end` |
| `pcf.geographyCountry` | `geography_country` if set; if null, omit ALL geography fields (= global) |
| `pcf.primaryDataShare` | `primary_data_share` as **string** |
| `pcf.dqi` | fixed conservative secondary-data scores, e.g. `{"coveragePercent": …}` — follow the vendored schema's required sub-fields |
| `pcf.exemptedEmissionsPercent` | `"0"` |
| `pcf.secondaryEmissionFactorSources` | `[{"name": "Open CEDA 2025", "version": "2025"}]` (shape per schema) |

**Authority order:** the vendored official schema (Step 5) wins over this table for exact field names/casing/required-ness in v3.0. Where they conflict, follow the schema and note the deviation in the PR description.

All decimal quantities serialize as strings (PACT rule: prevents float precision loss). Geography: our model only supports country-or-global; enforce that region/subdivision fields are never emitted alongside country.

## Step 3 — Backend: intake fields + export endpoints

**Modify `api/models/schemas.py`:**
- `SaveAnalysisRequest` gains optional fields: `product_description: str | None`, `reporting_period_start: date | None`, `reporting_period_end: date | None`, `geography_country: str | None` (validate ISO 3166-1 alpha-2: two uppercase letters, or None).
- Default reporting period when omitted: calendar year of the analysis date (Jan 1 – Dec 31).

**Modify `db/store.py` `save_analysis(...)`:** accept and insert the four new product columns (same defaults). `_line_item_row` adds `"data_source": "secondary"`.

**Modify `db/reader.py`:** extend `_PRODUCT_COLUMNS` with the new columns and `_LINE_ITEM_COLUMNS` with `data_source`.

**Modify `api/routes/analyzer.py`:**
- `POST /api/analyses` and `POST /api/analyze` (save path) pass the new fields through (Form fields on `/api/analyze`: `product_description`, `reporting_period_start`, `reporting_period_end`, `geography_country`, all optional).
- New endpoint:

```python
@router.get("/api/footprints/{product_id}/pact")
def export_pact(product_id: int, current_user: CurrentUser = Depends(get_current_user)) -> dict:
    # 404 if not found (reuse get_product_by_id)
    # 409 if product status != "approved" (detail: "Only approved footprints can be exported.")
    # build payload via exchange.pact.build_product_footprint
    # raise 500 with violations list if validate_product_footprint returns any (should never happen)
```

- Stretch (only if everything else is done): `GET /api/footprints` returning `{"data": [<payload>, ...]}` for the user's approved products — mirrors PACT's ListFootprints shape.

## Step 4 — Frontend: intake fields + export button

**Modify `frontend/src/app/analyzer/page.tsx`:**
- Add three optional inputs to the upload form: product description (text), reporting year (number input; convert to Jan 1 / Dec 31 dates when submitting), country of sale/manufacture (two-letter code select or text input, optional).
- After a successful save with status `approved`, show an "Export PACT payload" button.

**Modify `frontend/src/lib/api.ts`:**
- Pass the new fields in the save calls.
- New function `fetchPactPayload(productId: number): Promise<object>` calling `GET /api/footprints/{id}/pact` with the usual Bearer header.
- Export button opens a dialog (reuse existing dialog component in `frontend/src/components/ui/`) showing pretty-printed JSON with a copy button and a download-as-`.json` link.

Match the existing styling/components on the analyzer page. No new pages, no navigation changes (those are Phase 2).

## Step 5 — Tests + schema fixture

**Vendor the official schema:** download the PACT v3.0 ProductFootprint JSON schema from the `wbcsd/data-exchange-protocol` GitHub repo (v3 spec directory) into `tests/fixtures/pact_v3_product_footprint_schema.json`. Commit it. If the repo layout makes the exact file hard to find, STOP and report rather than hand-writing a schema.

**Add `jsonschema>=4.0.0` to `requirements.txt`.**

**New file `tests/test_pact_export.py`** covering at minimum:
1. A synthetic product dict (mirroring `get_product_by_id` output) serializes and **validates against the vendored schema** (this is the eval invariant).
2. All decimal fields in the payload are strings.
3. `geography_country=None` → no geography keys present; `geography_country="US"` → only `geographyCountry` present.
4. `primary_data_share` of 0 serializes as `"0"` (or schema-compliant equivalent).
5. `validate_product_footprint` catches a payload with a missing mandatory field.
6. Total-per-unit math: `pcf` emissions = `total_kg_co2e / unitary_product_amount`.

**Extend `tests/test_api.py`:** export endpoint returns 409 for a flagged product, 404 for missing (follow the existing test patterns/mocking in that file).

## Step 6 — Demo seed script

**New file:** `scripts/seed_demo.py` — CLI that (a) reads a sample BOM from `sample_boms/`, (b) runs the real pipeline (`parse_bom_csv` → `lookup_ef` → `calculate_footprint` → `run_critic`), and (c) saves via `db.store.save_analysis` for a user id + access token supplied via env vars (`SEED_USER_ID`, `SEED_ACCESS_TOKEN`). Idempotent enough to re-run (fine to create duplicate-named products; keep it simple). Document usage in a module docstring.

---

## Acceptance criteria (all must pass)

```bash
ruff check --ignore E501 evals tests calc parsing factors api llm copilot gap_analyzer rag db observability exchange
pytest tests -v                      # includes new test_pact_export.py
cd frontend && npm run lint && npm run build
```

Manual demo script (the phase gate — product owner walks this):
1. `uvicorn api.main:app` + `cd frontend && npm run dev`
2. Upload a sample BOM with description/year/country filled in → review → save as approved
3. Click "Export PACT payload" → JSON preview appears
4. Payload passes `pytest tests/test_pact_export.py` schema validation and `pcf.primaryDataShare` is `"0"`

## Out of scope for this phase (do not build)

Portfolio page, lifecycle statuses beyond existing approved/flagged, versioning behavior, PDS computation from primary data, scenario modeling, PACT `/events`, OAuth, dashboards.
