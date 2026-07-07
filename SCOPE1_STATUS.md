# Scope 1 — Working Status / Resume-Here
Living doc. Design lives in the implementation plan (`~/.claude/plans/lucky-growing-planet.md`) + research (`~/Downloads/Scope1Research/`). This is current position + gotchas.
_Last updated: 2026-07-07 · Branch: feature/scope1-v1 (off merged main e9ed8a8)_

## 1. Where we are
The Scope 1 (direct combustion emissions) MVP module is **merged to `main` via PR #24** and runs end-to-end against the shared Supabase dev DB. The defensible core is complete: org/entity/facility model → standards-correct per-gas engine → intake (manual/CSV/OCR/Bayou-PDF) → orchestration/readiness → GHG-Protocol/SB-253 reporting (+ PDF/XLSX) → audit/evidence → users & roles. Ships **dark** behind `NEXT_PUBLIC_SCOPE1_ENABLED`. Roadmap-wise we're ~80% through the MVP atomic-action list; remaining work is breadth/polish + the Bayou credential-connect automation (parked last, per user).

## 2. Done (all in PR #24)
- Data model + org-scoped RLS, migrations `030–039` — `588d1e7`
- Per-gas combustion engine + EPA EF library + selection hierarchy — `6cc9260`
- API + persistence + consolidation + reporting rollup — `52c1150`
- `/scope-1` frontend (dashboard/setup/collection/data/review/report) — `285d105`
- Data-collection orchestration + readiness meter — `a9bf923`
- Evidence upload (SHA-256 + Storage) + append-only audit log — `5c6001d`
- CSV bulk intake — `75f5b3a`
- Vision-LLM OCR (LangGraph + human-review queue) — `fb5089b`
- Bayou PDF bill-upload parser (Tier-2) + live-verified client — `7c48f63`, `eb48a66`
- SB 253 / GHG Protocol disclosure **PDF + XLSX** export — `7b5605b`
- Users & roles (admin/editor/viewer) — `42e0cfc`
- Hygiene: flag-gate nav, isolation lint, `DROP POLICY` guards, ci.yml revert — `a2bf85f`, `5afe586`

Post-merge (on `feature/scope1-v1`, not in PR #24):
- Incumbent / prior-year **base-year import** (A1b) — `f94b550` (no migration; reuses `s1_inventory.base_year*` cols; CSV or manual, source kept as evidence)

Files: `s1_calc/ s1_factors/ s1_consolidation/ s1_reporting/ s1_intake/{,ocr,bayou}`, `api/routes/scope1.py`, `db/scope1_store.py`, `api/models/scope1_schemas.py`, `api/graphs/scope1_ocr_graph.py`, `scripts/seed_scope1_reference.py`, `supabase/migrations/03[0-9]_*`, `frontend/src/app/scope-1/*`, `frontend/src/lib/scope1-api.ts`, `tests/test_s1_*.py`.

## 3. Decisions (+ why)
- **Migration band 030–039** (reserved lane; no collision with s2 040–049 / s3 050–059).
- **RLS = `public.is_org_member(org_id)`** everywhere (org-owned system-of-record data). We explicitly rejected `shares_org_with(user_id)` — it has a real bug: if the row's creator leaves the org, teammates lose access. Now the mandated standard for all 3 modules. `user_id`/`created_by` is audit metadata only, never in RLS.
- **Store gas masses (kg per species); NEVER store CO2e.** CO2e is derived at reporting time by applying a GWP version (AR5/AR6) at query time — one dataset serves US (AR5) + EU (AR6). AR6 splits CH4 into fossil 29.8 / biogenic 27.9. Biogenic CO2 is a separate memo line, excluded from the S1 total.
- **Roles: app-layer enforcement** via `require_scope1_role(min)` dependency (viewer<editor<admin). Default: org-admin→admin, member→editor. `s1_member_role` is Scope-1-owned (not a shared-`org_members` change). RLS-hard role enforcement is a V1 follow-up.
- **EF engine uses the canonical `EmissionFactorLibrary.default()`** (byte-identical to seeded `s1_ef_record`). DB-backed EF loader deferred (only matters for the annual admin EF-update story).
- **Bayou: PDF bill-upload (Option B) shipped; credential-connect (Option A) deferred** to the end of the queue.
- **PDF via `fpdf2`** (new dep); **XLSX via `openpyxl`** (already present).
- **Ships dark** via `NEXT_PUBLIC_SCOPE1_ENABLED`. CI/lint owned by the integrator (s1 packages not in the ruff path).

## 4. Gotchas & lessons  ← highest value
Shared (still true):
- CI runs `ruff check --ignore E501` on `evals tests calc parsing factors api llm copilot gap_analyzer rag db observability` — NOT `ruff format`, NOT the `s*_` dirs. E501 never fails CI; module packages aren't lint-gated. (I still self-lint s1_* locally.)
- `CREATE POLICY` isn't idempotent — every one is preceded by `DROP POLICY IF EXISTS` so migrations re-run cleanly.
- Inserting explicit `null` overrides a column DEFAULT → NOT NULL violation. Drop None fields on insert (`req.model_dump(exclude_none=True)`).
- Migrations are applied **by hand** (Supabase SQL Editor / psycopg) to a **shared dev DB all 3 agents use**; merging code does NOT apply them. `030–039` are applied to dev; **prod still needs them**.
- Migration band: S1 = 030–039 (S2 040–049, S3 050–059). **NOW FULL (all 10 used).** Any future s1 schema change needs a band decision from the integrator — do NOT reach into 040+ (Scope 2). Reuse existing columns/tables where possible (e.g. base-year import reused `s1_inventory.base_year*`).
- Ships dark via `NEXT_PUBLIC_SCOPE1_ENABLED`.

Scope-1-specific (cost real time):
- **`fpdf2` core fonts are Latin-1 only.** Any Unicode in user data (e.g. a facility named "Café Plânt") crashes the PDF. All dynamic text goes through `_pdf_safe()` (`s1_reporting/export.py`). Don't remove it.
- **`fpdf2` is a new dep** in `requirements.txt`. It's NOT in the shared `.venv`; it's installed isolated at `<scratch>/exportlibs`. **Run any suite that touches export/roles/api tests with `PYTHONPATH=<scratch>/exportlibs`** or you get `ImportError`. CI/deploy installs it from requirements.
- **LangGraph OCR tests need `MemorySaver`, not the Postgres checkpointer.** That setup is a **module-local autouse fixture in `tests/test_s1_ocr.py`** (reset `scope1_ocr_graph._ocr_graph = None` + patch `get_checkpointer`). It is deliberately NOT in the shared `tests/conftest.py` (hygiene #5). Any new graph needs the same local fixture.
- **The write-route auth swap (`require_editor`) breaks route tests that don't mock the role.** `tests/test_s1_api.py` has a module-local autouse fixture defaulting `db.scope1_store.get_scope1_role` → `"admin"` so handler tests still run; role gating itself is tested in `tests/test_s1_roles.py`.
- **Role enforcement is app-layer ONLY.** RLS still lets any org member write, so a viewer with the anon key could bypass via direct Supabase calls. Acceptable (app is the only client); RLS-hardening (`s1_can_edit`) is the V1 fix.
- **Bayou real API** (verified live): base `https://bayou.energy/api/v2` (NOT `api.bayou.energy`); HTTP Basic auth with the API key as the **username, blank password**; bill `status` field values `unlocked`/`unlocked_for_gas` = parsed; meter is a `meters[].id` array. **Uploading + unlocking a bill costs ~$2 on a LIVE key** — do NOT test the upload path on a live key. The `BAYOU_API_KEY` in local `.env` is currently a **live** key (prod key belongs in Railway env, not the repo).
- **Anthropic**: model `claude-sonnet-4-6`; vision via a `document` content block for PDFs, `image` block for images (`s1_intake/ocr/extract.py`). The LLM call is injectable so parse/confidence logic is unit-tested keyless.
- **Evidence needs the private Supabase Storage bucket `s1-evidence`** (already created) — it's storage, not a table. SHA-256 is computed server-side.
- **Offline migration validation:** `pglast` is installed at `<scratch>/pglibs`; parse-check migrations with it (no local Postgres exists).
- **Worktree isolation:** this is a `git worktree`; the Python `.venv`, `frontend/node_modules`, and `.env` are the **original repo's, shared** (symlinked). Never edit the shared root `.env`. Local full-stack run uses **non-default ports** (uvicorn `8001`, `next dev -p 3021`) to avoid colliding with the scope2/scope3 agents, with an isolated `frontend/.env.local` (`NEXT_PUBLIC_BACKEND_URL=http://localhost:8001`).

## 5. How to run / test
Paths: `ORIG=<repo>/product-footprint-analyzer` (has `.venv`, `node_modules`), `WT=<repo>/product-footprint-analyzer-scope1` (this worktree), `SCRATCH=.../scratchpad`.
- **Backend tests:** `cd $WT && PYTHONPATH=$SCRATCH/exportlibs ANTHROPIC_API_KEY="" $ORIG/.venv/bin/python -m pytest tests -q` (208 passing).
- **Ruff:** `$ORIG/.venv/bin/ruff check --ignore E501 <paths> s1_calc s1_factors s1_consolidation s1_reporting s1_intake`.
- **Frontend:** `cd $WT/frontend && npm run lint && npm run build` (node_modules symlinked).
- **Migrations:** apply by hand via Supabase SQL Editor, or `psycopg.connect(os.environ["DATABASE_URL"])` from `.env`. `030–039` already on dev DB.
- **Seed reference data:** `$ORIG/.venv/bin/python scripts/seed_scope1_reference.py` (service-role; idempotent).
- **Env/creds** (`.env`, gitignored, symlinked): `SUPABASE_URL/ANON/SERVICE_ROLE_KEY`, `DATABASE_URL`, `BAYOU_API_KEY` (live), `ANTHROPIC_API_KEY`. Frontend flag: `NEXT_PUBLIC_SCOPE1_ENABLED=true`.
- **Live full-stack:** `uvicorn api.main:app --port 8001` + `cd frontend && npm run dev -- -p 3021`; open `http://localhost:3021`, log in, `/scope-1`.

## 6. Next up / deferred
- **Next (MVP breadth):** ~~(3) incumbent / prior-year import (A1b)~~ ✅ done `f94b550`. (4) guided onboarding wizard + checklist (P1), (5) admin annual EPA EF update / DB-backed EF loader (C1).
- **Parked to end (Bayou lane, user's call):** (6) Bayou credential-connect auto-pull (Option A), (7) connection management — health/re-auth/sync (P5).
- **V1 (explicitly out of MVP):** base-year recalculation engine, refrigerant/fugitive, process emissions, Samsara live telematics, ESRS/CDP/GHGRP exports, Scope 2 bolt-on, RLS-hard role enforcement, SOC 2, email display in the roles UI (currently truncated `user_id`).
- **Integration follow-up:** the three `s{N}_member_role` tables may be consolidated into one shared roles model (integrator's call).

## 7. Open questions
- CA SB 253's exact 2027 template/portal/API is undefined until CARB rulemaking — our export is a thin mapping designed to absorb it; revisit when published.
- Bayou credential-connect onboarding/webhook-vs-poll flow needs verification against a **test** key before building.
- Harden roles at the RLS layer (V1) vs keep app-layer (MVP) — decision pending real multi-tenant security review.
