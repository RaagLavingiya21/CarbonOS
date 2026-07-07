# Scope 2 ("Grid") — Working Status / Resume-Here

**Living doc.** Distilled state so a fresh session resumes instead of re-deriving.
Design lives in `SCOPE2_IMPLEMENTATION_PLAN.md`; this is current position + gotchas.
Update it at the end of each work chunk.

_Last updated: 2026-07-06 · Branch: `feature/scope2-v1` (off `main` after PR #24)_

---

## 1. Where we are
The **Scope 2 MVP is feature-complete** (PRD §5, all of M0–M3) and **merged to `main`**
via PR #24 (`integration/scopes`), shipping **dark** (nav flag off). It's one isolated
`s2_*` module on the Carbon OS platform, sharing infra (auth, DB client, deploy, shadcn
UI) but no business logic/data with Scope 1/3 or the Scope 3/PACT product. ~230 tests,
CI-green. Next work = M1 ingestion hardening + post-MVP (V1 compliance).

## 2. Done (shipped)
- **M0** — data model (migrations `040–046`), dual-method calc engine (LB + market-based,
  8 GHGP EAC criteria, sourcing hierarchy, proration), versioned factor library
  (vintage pinning), sector site templates, **eGRID subregion resolution**, CSV import +
  unit normalization, immutable audit log, **factor-seeding loader** (`scripts/seed_s2_factors.py`).
- **M1 (partial)** — CSV **commit** path (persists accounts+bills, resolves site by name).
- **M2** — **leased-site landlord data-request workflow** (the wedge), **documented
  estimation fallback** (floor-area × sector intensity, audit-labeled), **data-quality /
  coverage scoring** (dashboard readiness KPI).
- **M3** — **reporting**: standard/CDP/Amazon export (config-driven mappings) + CSV, and
  the **inbound buyer request queue** (deadlines, overdue derivation, answer linkage).
- Frontend `/scope-2/*`: dashboard (coverage KPI), sites (+eGRID+CSV), calculate,
  landlord (+estimation), reports (+queue). All behind `NEXT_PUBLIC_SCOPE2_ENABLED`.
- Isolation import-lint (`tests/test_scope2_isolation.py`) forbids Carbon OS **and**
  sibling-scope (`s1_*`/`s3_*`) imports — scans packages, routes, stores, schemas.

## 3. Decisions (+ why)
- **Migration band `040–049`** — reserved; S1 owns `030–039`, S3 `050–059`. Never cross.
- **Org-scoped RLS** (not user-only) — multi-staff customers; reuse `shares_org_with`;
  resolve `org_id` in the **route** layer (`scope2_deps`), stores import only `db.client`.
- **Aggregator provider deferred** — keep `s2_ingestion/aggregator.py` interface abstract;
  pick Arcadia vs UtilityAPI once a design partner's utilities are known.
- **Reporting order: CDP → Amazon** (fast-follow Walmart/EcoVadis). CDP covers 380+ buyers;
  Amazon requires both LB+MB (exercises the wedge). Mappings are config, not code.
- **Ships dark** via feature flag; nav hidden until GA.
- **eGRID subregion is user-selected** (form dropdown, 26 EPA codes) — no fabricated
  ZIP→subregion crosswalk; a missing subregion falls back to `iea/US` national average.
- **Factor values are never fabricated** — sample factors are labeled `SAMPLE`; real data
  loads via `scripts/seed_s2_factors.py` from a cited CSV.

## 4. Gotchas & lessons (the expensive-to-learn stuff)
- **Insert with `exclude_none=True`.** Sending an explicit `null` overrides a column
  DEFAULT and trips NOT NULL (hit this on site create). Drop None fields so DB/template
  defaults apply.
- **`CREATE POLICY` is NOT idempotent** (no `IF NOT EXISTS`). Precede every one with
  `DROP POLICY IF EXISTS <name> ON <table>;` so migrations re-run cleanly. (Migrations
  `040–046` early on lacked this; `043`/`044` have it. Consider back-filling.)
- **CI runs `ruff check --ignore E501`** on `evals tests calc parsing factors api llm
  copilot gap_analyzer rag db observability` — NOT `ruff format`, and NOT the `s*_` module
  dirs. So E501 never fails CI, and module packages aren't lint-gated by CI.
- **Migrations are applied by hand** (Supabase SQL Editor) to a **shared dev DB** all three
  agents use. Merging code does NOT apply them — track per-environment. Prod (Vercel/
  Railway from `main`) still needs S3 migrations + flags flipped.
- **Local full-stack auth**: frontend + backend must point at the **same** Supabase project;
  browser session is per-origin (`localhost:3000`). Test user is created via service-role
  admin API (email_confirm=true).
- **Supabase branching wasn't used** — everything's the one project. Be careful with DDL.

## 5. How to run / test (local)
- **Backend**: `.venv/bin/uvicorn api.main:app --reload` on `:8000` (serves all mounted
  scope routers). Env in `.env` (`SUPABASE_URL`, keys, `DATABASE_URL`, `DEMO_ORG_ID`).
- **Frontend**: `cd frontend && NEXT_PUBLIC_SCOPE2_ENABLED=true npm run dev` on `:3000`
  (add `SCOPE1/3_ENABLED=true` to show those nav entries). `.env.local` has
  `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000` + Supabase public keys.
- **Test user**: `scope2demo2dabdc@example.com` / `Grid-TwLyVkJrs1uyIQ` (demo org auto-joined
  on first authenticated request via `ensure_demo_membership`).
- **Checks**: `.venv/bin/python -m pytest -q` · `.venv/bin/python -m ruff check <files>` ·
  `cd frontend && npm run build && npm run lint`.
- **Flow**: sites (+eGRID+CSV import) → calculate → coverage KPI → landlord (+estimate) →
  reports (CDP/Amazon + request queue).

## 6. Next up / deferred
- **M1 hardening**: aggregator adapter (provider TBD), PDF/OCR bill extraction (Claude
  vision), estimated-read/true-up **dedup** (`superseded_by_bill_id` schema is ready, logic
  isn't).
- **Back-fill `DROP POLICY IF EXISTS`** into migrations `040–042`, `045`, `046` for idempotency.
- **Real factor data** — replace sample factors with cited eGRID/IEA/Green-e via the loader.
- **V1 (compliance-grade)**: EAC registry linkage, SB253 + CSRD ESRS E1 generators,
  assurance-ready export, target-setting. **V2**: procurement decision support + MACC.
  **V3**: hourly matching. (Full roadmap: `SCOPE2_IMPLEMENTATION_PLAN.md` §6, synthesis §7–8.)

## 7. Open questions
- First aggregator (Arcadia vs UtilityAPI) and first buyer template (Walmart vs Amazon vs
  EcoVadis) — both design-partner-driven; revisit when pilots are known.
- Residual-mix default for non-Green-e US RECs (documented gray area).
- Prod migration discipline — adopt Supabase migration CLI vs. manual SQL Editor.
