# Wave 4 Implementation Plan — "Scale the Front Door" (Establish)

**Executes:** the top un-addressed gap in `PRODUCT_STRATEGY.md`'s gap analysis (the "Establish" bottleneck). Read `PRODUCT_STRATEGY.md`, `PCF_PLATFORM_DESIGN.md`, and `CLAUDE.md` first.
**Branch:** `feature/wave-4-front-door`.

> **Base confirmed.** This branch sits on top of the merged Wave 3 (`supabase/migrations/028_product_volumes.sql` is present on the base), so this wave's migration is numbered **`029`** with no collision. Ready to implement directly — no rebase needed.

## Why
Two gaps make the "front door" the bottleneck for a real portfolio: analysts get **one product in at a time**, and when the emission-factor match is wrong they can **flag but not fix** it — and the fix doesn't stick, so the same messy material gets re-corrected forever. Wave 4 makes ingestion bulk and makes factor corrections institutional knowledge.

## Instructions for the implementer
- Implement exactly what this says. If something is ambiguous or looks wrong, STOP and report — do not improvise.
- Commit in small logical steps. Two workstreams (A bulk, B overrides) — reasonable as two PRs. Test the migration on a local DB first. Never write credentials into source files.
- **Preserve the dependency rule:** `factors/ef_lookup.py` is pure and must NOT import from `db/`. Overrides are passed *into* `lookup_ef` as a parameter by the caller.

## Locked decisions
1. **Bulk = multiple CSV files in one upload**, each file → one product, run through the existing pipeline; a per-file results summary (saved vs flagged vs error). One bad file must not abort the batch.
2. **EF overrides are org-wide** — a correction is stored per org and benefits every analyst's *future* matches. Applies to future matches + an explicit per-line **re-map** that creates a new footprint version. **Never silently recomputes existing published footprints** (immutability).
3. Engine stays spend-based. This wave improves *matching and ingestion*, not the calculation method.

## Do-NOT-touch
- `parsing/`, `calc/*`, `exchange/*`, Wave 1–3 logic (call/read only)
- The purity of `factors/ef_lookup.py` — extend its signature, don't add DB imports
- Footprint immutability — a re-map creates a new version, never edits a published row
- Existing migrations `001`–`028`; `app.py`, `pages/`, `.github/workflows/`

---

## Workstream A — Bulk multi-product import

**A1. Backend (`api/routes/analyzer.py`)** — `POST /api/analyze/bulk` accepting `list[UploadFile]`. For each file: run the existing pipeline (`parse_bom_csv` → factor matching *with overrides from Workstream B once available; without until then* → `calculate_footprint` → `run_critic` → `save_analysis`). Wrap each file in try/except so one failure doesn't abort the batch. Return `{results: [{filename, product_id?, product_name?, total_kg_co2e?, flagged_items?, status: "saved"|"error", error?}]}`. Extract the single-file pipeline into a shared helper if not already, and reuse it here (do not duplicate the calc logic).

**A2. Frontend (`frontend/src/app/analyzer/page.tsx` or a bulk sub-view)** — a multi-file drop zone + "Analyze N files" → calls the bulk endpoint → a **results table** (filename → product link, or an error row). Each saved product links to `/analyzer/{product_id}`. Reuse existing table/`Badge`/`Card` components. `api.ts` gets `analyzeBulk(files)`.

**A3. Tests** — bulk endpoint creates N products from N valid files; a malformed file returns an `error` row without failing the batch; the summary counts match.

---

## Workstream B — EF override that sticks + factor picker + per-line re-map

**B1. Migration `supabase/migrations/029_ef_overrides.sql`** — `ef_overrides`: `override_id BIGSERIAL PK`, `org_id UUID` (nullable — set for org-scoped, null for personal), `user_id UUID NOT NULL REFERENCES auth.users`, `material_normalized TEXT NOT NULL` (lowercased/trimmed), `sector_code TEXT NOT NULL`, `sector_name TEXT`, `created_at`, `updated_at`. Unique on `(org_id, material_normalized)` where org set, else `(user_id, material_normalized)`. RLS: org members read org overrides; owner reads personal; writes by members/owner.

**B2. `factors/ef_lookup.py` (keep pure)** — add `overrides: dict[str, str] | None = None` to `lookup_ef(material, country=None, overrides=None)`. Normalize the material; if it's a key in `overrides`, resolve the EF for that `sector_code` + country directly (confidence **100**, `source_citation` noting "analyst override", `is_low_confidence=False`). Otherwise the existing static-mapping → fuzzy → sector-fallback flow is unchanged. No DB import — the dict is passed in.

**B3. `db/ef_override_store.py` (new)** — `get_active_overrides(access_token, *, user_id) -> dict[str,str]` (material_normalized → sector_code) for the caller's active org (reuse `db.org_store.get_active_org_member_ids`/active org), else personal. `set_override(material, sector_code, sector_name, *, user_id, access_token)` (upsert; audit-log), `list_overrides(access_token, user_id)`, `delete_override(override_id, ...)`.

**B4. Wire overrides into matching** — the factor-matching path (single `POST /api/analyze`, `/api/analyze/match-factors`, and the bulk endpoint) loads overrides via `get_active_overrides` and passes them to `lookup_ef`. One shared helper so single + bulk behave identically.

**B5. Factor picker + override + re-map API (`api/routes/analyzer.py` or new `api/routes/factors.py`)** —
- `GET /api/factors/sectors?q=` → searchable CEDA sector list (reuse `factors.ef_lookup.get_all_sector_names` + codes) for the picker.
- `POST /api/ef-overrides` (material, sector_code) / `GET /api/ef-overrides` / `DELETE /api/ef-overrides/{id}`.
- `POST /api/analyses/{product_id}/remap-line` (body: `item_id`, `sector_code`, `save_override: bool`): re-match that line to the chosen sector, recompute `kg_co2e = spend × new_ef`, and **create a new footprint version** (reuse the Phase 3 versioning/clone path in `db/store.py`, same mechanism as `apply_primary_data`). If `save_override`, also persist the material→sector override so future matches use it. Returns the new version + delta.

**B6. Frontend** —
- On the EF-review / line-item table (analyzer flow and `/analyzer/[id]`): for a low-confidence or wrong match, a **"Re-map"** action → a **searchable factor picker** (sector search via the new endpoint) → choose sector → recompute (new version) with an optional "save this mapping for our org" checkbox.
- A **"Factor mappings"** management view (settings or a small page): list saved org overrides, delete them.
- `api.ts`: sector search, override CRUD, `remapLine`.

**B7. Tests** — `lookup_ef(..., overrides={...})` returns the overridden sector at confidence 100; `get_active_overrides` is org-scoped; `remap-line` creates a new version with the corrected EF + recomputed total (baseline version unchanged); saving an override then matching the same material uses it; picker search returns matching sectors.

---

## Acceptance criteria (whole plan)
```bash
ruff check --ignore E501 evals tests calc parsing factors api llm copilot gap_analyzer rag db observability exchange
pytest tests -v
cd frontend && npm run lint && npm run build
```
Manual demo: drop 3 BOM files at once → all 3 become products in one pass, a bad file flagged not fatal → open a product with a wrong low-confidence match → **Re-map** it via the searchable picker, tick "save for our org" → footprint gets a new version with the corrected number → upload a *new* BOM containing that same material → it now matches correctly at high confidence automatically.

## Out of scope (Wave 4)
The activity-based / hybrid engine (still spend-based); ERP/PLM API integration (manual multi-file only); auto-retroactive recompute of existing footprints when an override is saved; ML-learned mappings (explicit analyst overrides only).

## Review lens (post-implementation)
`factors/ef_lookup.py` stays import-pure (overrides passed in, not read from DB inside it); override scoping is correct (org vs personal, RLS enforced); re-map creates a new version and never mutates a published row; the bulk endpoint isolates per-file failures; the usual "mocks-pass-but-production-breaks" (RLS on `ef_overrides`, override normalization mismatch between save and lookup).
