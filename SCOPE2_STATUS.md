# Scope 2 ("Grid") — Working Status / Resume-Here

**Living doc.** Distilled state so a fresh session resumes instead of re-deriving.
Design lives in `SCOPE2_IMPLEMENTATION_PLAN.md`; this is current position + gotchas.
Update it at the end of each work chunk.

_Last updated: 2026-07-07 · Branch: `feature/scope2-v1` (off `main` after PR #24)_

---

## 1. Where we are
The **Scope 2 MVP is feature-complete** (PRD §5, all of M0–M3) and **merged to `main`**
via PR #24 (`integration/scopes`), shipping **dark** (nav flag off). It's one isolated
`s2_*` module on the Carbon OS platform, sharing infra (auth, DB client, deploy, shadcn
UI) but no business logic/data with Scope 1/3 or the Scope 3/PACT product. 419-test
suite, CI-green.

**V1 in progress on `feature/scope2-v1`** (local, unpushed). M1 ingestion hardening done:
true-up dedup (`115022c`), overlap dedup (`eb2ef11`), aggregator adapter (`d22a63b`),
idempotent migrations (`bcdd94d`), multi-meter PDF/OCR + evals + routes + UI (`fbe81ef`…
`203261f`). **V1 compliance**: SB 253 + CSRD ESRS E1 disclosure generators + UI (`9fd8e54`, `afc5073`)
**EAC registry linkage** (`afcacd6`, `1b67579`), and **assurance-ready XLSX/PDF export**
(`d055813`, `227d722`). Next V1 = target-setting. ⚠ migrations 047 + 048 unapplied.

## 2. Done (shipped)
- **M0** — data model (migrations `040–046`), dual-method calc engine (LB + market-based,
  8 GHGP EAC criteria, sourcing hierarchy, proration), versioned factor library
  (vintage pinning), sector site templates, **eGRID subregion resolution**, CSV import +
  unit normalization, immutable audit log, **factor-seeding loader** (`scripts/seed_s2_factors.py`).
- **M1 (partial)** — CSV **commit** path (persists accounts+bills, resolves site by name);
  **true-up / estimated-read dedup** (`s2_ingestion/dedup.py`: actual > estimated >
  cost-only per exact account+period; applied after every CSV commit + estimate via
  `s2_bill_store.supersede_bills`; commit response carries `superseded_count`);
  **provider-agnostic aggregator adapter** (`s2_ingestion/aggregator.py`: RawBill/RawAccount +
  `AggregatorProvider` Protocol + `map_raw_bill` + `FakeAggregatorProvider` + registry —
  no real vendor bound yet; `get_provider` raises for un-wired names);
  **multi-meter PDF/OCR extraction** (`s2_ingestion/ocr.py`: Claude-vision, injectable
  invoke, per-field confidence, review flags; elec+gas; own REVIEW_THRESHOLD, isolated)
  via routes `POST /api/scope2/bills/extract-doc` (stateless preview) + `import-doc`
  (commit, `ingestion_method='pdf_ocr'`, feeds dedup). **Two-tier OCR eval** in
  `evals/scope2_ocr/`: platform-agnostic scoring (field acc, end-to-end MWh, review
  precision/recall, cost/latency), deterministic golden tier in CI + manual
  `run_live.py` for real redacted bills (README documents the label schema).
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
  `DROP POLICY IF EXISTS <name> ON <table>;` so migrations re-run cleanly. ✅ **Done** —
  all Scope 2 migrations `040–046` now do this (`bcdd94d`). Follow the same pattern in
  any new migration.
- **Dedup runs two passes** (`s2_ingestion/dedup.py`): exact-period (authority rank), then
  **coverage** — an estimate is superseded by overlapping *actuals* once they cover ≥90%
  (`COVERAGE_THRESHOLD`) of its period. So a full year of monthly actuals replaces the
  annual floor-area estimate, but a single month does not (would drop 11 months). Known
  gap: during *partial* accumulation (<90%) the estimate and the partial actuals both
  count → transient double-count for the covered months (same as before; not auto-resolved).
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
- **Flow**: sites (+eGRID+CSV import) → import (PDF/OCR review) → EACs (RECs/GOs) → calculate →
  coverage KPI → landlord (+estimate) → reports (CDP/Amazon + SB253/CSRD disclosure + queue).
- **Unapplied migrations** (apply to the shared dev DB / prod before those features work):
  `047_s2_eac_instruments`, `048_s2_calc_renewable_mwh`.

## 6. Next up / deferred
- **M1 hardening**: ✅ true-up/estimated-read **dedup** · ✅ **aggregator adapter** interface
  (bind Arcadia/UtilityAPI + a pull route when a partner's utilities are known) · ✅
  **PDF/OCR extraction + eval scaffold + routes**. Remaining M1:
  - ✅ **OCR frontend upload UI** done — `/scope-2/import` (`203261f`): site select → file→
    base64 upload → `extract-doc` → per-meter review cards (confidence + flags, inline edit,
    drop rows) → `import-doc`; result banner shows committed/superseded/skipped.
  - **Real-doc OCR evals** — drop redacted bills + labels into `evals/scope2_ocr/` and run
    `run_live.py`; use review-recall to **calibrate `REVIEW_THRESHOLD`** (currently 0.85,
    a guess). Decide then whether to push live runs to LangSmith (scoring is decoupled).
    **This needs your redacted bills — it's the main open M1 item.**
- ✅ **Overlap dedup** done (`eb2ef11`) — annual estimate vs. monthly actuals (≥90% coverage).
  Remaining polish: flag/surface the partial-coverage (<90%) transient double-count (§4).
- ✅ **Migration idempotency back-fill** done (`bcdd94d`).
- **Real factor data** — replace sample factors with cited eGRID/IEA/Green-e via the loader.
- **V1 (compliance-grade)** — in progress:
  - ✅ **SB 253 + CSRD ESRS E1 disclosure generators** done (`9fd8e54` backend, `afc5073` UI):
    `s2_reporting/compliance.py` (structured sections + assurance-readiness gate), routes
    `GET /disclosure-standards` + `/calculations/{id}/disclosure?standard=`, and the
    disclosure view on `/scope-2/reports`. Config-driven; template drift = data change.
  - ✅ **EAC registry linkage** done (`afcacd6` backend, `1b67579` UI) — `s2_eac_instruments`
    (migration 047) + CRUD (`db/s2_eac_store.py`, `scope2_eac` routes, `/scope-2/eacs` UI).
    Calc loads EACs for the year → engine quality-screens (8 GHGP criteria) → market-based
    reflects real coverage; EAC-covered MWh persisted (`renewable_mwh`, migration 048) →
    feeds CSRD ESRS E1-5 renewable mix (closed that readiness warning).
    **⚠ migrations 047 + 048 must be applied to the shared dev DB (and prod) before use.**
  - ✅ **Assurance-ready export** done (`d055813` backend, `227d722` UI) — `s2_reporting/export.py`
    build_disclosure_xlsx (field-tagged + readiness sheet) / build_disclosure_pdf (readiness
    banner + per-section tables); routes `/calculations/{id}/disclosure.xlsx` + `.pdf`; XLSX/PDF
    download buttons on `/scope-2/reports`. (fpdf2 gotcha: multi_cell needs `new_x=LMARGIN`.)
  - **Target-setting** (next) — base-year + reduction trajectory (SBTi-style) against the dual-method totals.
  **V2**: procurement decision support + MACC.
  **V3**: hourly matching. (Full roadmap: `SCOPE2_IMPLEMENTATION_PLAN.md` §6, synthesis §7–8.)

## 7. Open questions
- First aggregator (Arcadia vs UtilityAPI) and first buyer template (Walmart vs Amazon vs
  EcoVadis) — both design-partner-driven; revisit when pilots are known.
- Residual-mix default for non-Green-e US RECs (documented gray area).
- Prod migration discipline — adopt Supabase migration CLI vs. manual SQL Editor.

## V2 Status (2026-07-07 ongoing)

### Priority 1 — Target-Setting (SBTi-style reduction tracking) ✅

**Complete:** Org-level base-year + future target (amount or % reduction) with org-scoped RLS.

**Backend:**
- Migration 049: s2_targets table with immutable base/target totals, mutable status/notes
- Store: s2_targets_store.py with list/get/create/update/delete 
- Schemas: CreateTargetRequest, TargetDTO with from_row() factory
- Routes: GET /targets (list), GET /targets/active, POST /targets (create with validation), PATCH (update status/notes), DELETE
- Tests: list_targets, create_target, create_target_needs_amount_or_pct (all passing)
- Suite: 560 passing

**Frontend:**
- Page: /scope-2/targets with empty state, active target highlight, other targets list
- Create form: year selectors (1975–2075), base-year + target emissions, absolute/percentage toggle, trajectory type (linear/exponential), optional notes
- Progress card: displays base/target emissions, % reduction, progress bar, status badge
- Linked from main /scope-2 dashboard
- Build: Next.js passes cleanly

**Commits:** c423cec (backend), 66a8c73 (frontend)

### Next Priorities

**Priority 2:** Real-doc OCR evals (user supplies redacted bills → calibrate REVIEW_THRESHOLD ~0.85)
**Priority 3:** Aggregator binding (fetch real PDFs from provider, pipe to OCR intake)

### Pending DB Tasks
- Apply migration 049 to dev/prod databases

### Priority 2 — OCR eval corpus + REVIEW_THRESHOLD calibration ✅ (infra)

Synthetic-first (no real bills yet). All under `evals/scope2_ocr/` + one config knob.

**Built:**
- `synthetic.py` — Pillow bill-image generator; BillSpec/MeterSpec; clean/moderate/hard difficulty tiers (blur, rotation, low-res, fade, seeded noise); auto-labels with `canonical_mwh` from the real `normalize_to_mwh`. Deterministic per seed.
- `generate_corpus.py` — CLI writing `<name>.png` + `<name>.json` pairs into a gitignored `corpus/` dir.
- `calibration.py` — pure `Observation`/`sweep_threshold`/`recommend_threshold` (smallest cutoff meeting review-recall floor, default 0.95) + `observations_from_rows`.
- `run_calibration.py` — API-gated live runner: extract→score→sweep→recommend; JSON report.
- `langsmith_tracking.py` — opt-in, eval-layer-only adapter (`S2_OCR_LANGSMITH=1` + key); lazy-imports langsmith; logs experiment metrics + recommended threshold + dataset. Production OCR path stays LangChain-free. No-op + offline when disabled.
- `s2_ingestion/ocr.py` — `REVIEW_THRESHOLD` now env-overridable (`S2_OCR_REVIEW_THRESHOLD`, default 0.85) so a calibrated value deploys without code change.
- New golden case `degraded_lowconf_elec` (correct read, low confidence → review false-positive) guards the threshold path.
- Tests: synthetic determinism/labels/tiers, calibration precision-recall math, langsmith no-op-when-disabled, threshold env override. Full suite 613 passing, ruff clean.

**Remaining (needs a key):** one live `run_calibration` pass over a generated corpus to read the recommended threshold, set it as the default, and confirm review_recall ≥ 0.95. Synthetic bills are a proxy for real scan messiness — re-calibrate on real redacted bills when available (drop them in the gitignored corpus dir).

### P2 calibration run + empty-extraction fix (2026-07-08)

Ran the live calibration over a 30-bill synthetic corpus (seed 0). Outcome: the
threshold sweep was **flat** — extracted meters came back ≥0.99 confidence and
correct, so there was no signal to move REVIEW_THRESHOLD (recommended 0.50 is a
degenerate "everything passes" artifact). **Kept the default 0.85.** Real
threshold calibration needs real messy bills; synthetic renders are too legible.

The run *did* surface a real gap: **4/30 bills failed extraction entirely** (model
returned no meters) — invisible to the per-meter review metric and silently
excluded from the MWh coverage rate. Fixed:
- `s2_ingestion/ocr.py::bill_review_reasons` — bill-level review reasons (errored,
  or zero meters extracted).
- `extract-doc` route now routes empty/failed extractions to review (was
  `needs_review=False`) and returns bill-level `review_reasons` (schema updated).
- Scorecard tracks `extraction_empty` per case + `extraction_failure_rate`
  aggregate; new golden case `empty_extraction`.
- Tests: bill_review_reasons unit, extract-doc empty-extraction route, golden
  empty-extraction. Suite 616 passing, ruff clean.

Threshold calibration itself is **deferred to real redacted bills** (drop into the
gitignored corpus dir, `run_calibration` re-usable as-is).
