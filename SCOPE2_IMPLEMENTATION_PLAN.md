# Scope 2 ("Grid") — Technical Implementation Plan on the Carbon OS Platform

**Status:** Draft v1 · 2026-07-04
**Branch:** `feature/scope2-mvp` (forked from `origin/main` @ `96e5622`)
**Source PRD:** `Scope2Research/deliverables/PRD-MVP.md`
**Source research:** `Scope2Research/research/SYNTHESIS-product-strategy.md`, node records L1.1–L1.5
**Platform docs:** `Architecture_Decisions.md`, `CLAUDE.md`, `PCF_PLATFORM_DESIGN.md`

---

## 0. Guiding principle: an isolated module on shared rails

Scope 2 ("Grid") is built as a **self-contained vertical module** that reuses the Carbon OS **infrastructure and conventions** but shares **no business logic or data** with the existing Product Carbon Footprint (Scope 3 / PACT) product. Per the brief: clicking anything Scope 2 does not read from or write to any Carbon OS footprint/BOM/supplier data. Same deployment, same auth, same design system — separate domain.

This mirrors the pattern the team already started for Scope 1 (`s1_calc/`, `s1_factors/`, `s1_consolidation/`, `s1_reporting/`). Scope 2 follows the **same `s2_*` module convention**, so the codebase reads consistently and a future "one platform, all scopes" merge is a routing/navigation exercise, not a re-platform.

### What we REUSE (shared rails — do not fork)
| Concern | Reuse | Why |
|---|---|---|
| Auth | `api/middleware/auth.py` → `get_current_user` / `CurrentUser` | One identity, one login. Every Scope 2 route depends on the same JWT middleware. |
| DB client + RLS | `db/client.py` → `get_user_client(access_token)` | Same Supabase project, same RLS-per-JWT tenancy model. New tables, same enforcement. |
| Deploy | Vercel (frontend) + Railway (`Dockerfile`, FastAPI) | Scope 2 routers mount into the same FastAPI app; Scope 2 pages ship in the same Next.js build. No new infra. |
| Design system | `frontend/src/components/ui/*` (shadcn), theme, `app-shell` | Consistent look; Scope 2 pages feel native. |
| LLM client | `anthropic` SDK already in `requirements.txt` | For bill OCR extraction + CSV column-mapping assist. Default to the latest Claude model (Opus 4.8 / `claude-opus-4-8`). |
| Conventions | Numbered migrations, `*_store.py`, Pydantic DTOs w/ `from_row`, `lib/<domain>-api.ts` | Zero new patterns to learn. |

### What we ISOLATE (net-new, `s2_`/`scope2_` namespaced — no cross-imports)
- All business-logic modules: `s2_ingestion/`, `s2_sites/`, `s2_factors/`, `s2_calc/`, `s2_reporting/`, `s2_quality/`.
- All DB tables (prefix `s2_`) + their stores (`db/s2_*_store.py`).
- All API routers (`api/routes/scope2_*.py`, all paths under `/api/scope2/...`).
- All frontend routes under `/scope-2/*` + `frontend/src/lib/scope2-api.ts`.

### The only shared files Scope 2 touches (append-only, additive)
1. `api/main.py` — add `app.include_router(scope2_*.router)` lines (append to the existing block).
2. `frontend/src/components/app-shell.tsx` — add **one** entry (`{ href: "/scope-2", label: "Scope 2", ... }`) to the `navItems` array. Optionally gate behind a feature flag.
3. `supabase/migrations/` — add new files starting at `030_*` (never edit existing migrations).
4. `requirements.txt` — add any new Python deps (e.g. an OCR/aggregator SDK) as additional lines.

> **Isolation guardrail (enforceable in CI):** no file under `s2_*/`, `api/routes/scope2_*.py`, or `db/s2_*_store.py` may import from `calc/`, `factors/`, `parsing/`, `gap_analyzer/`, `copilot/`, `rag/`, `exchange/`, or the existing non-`s2` `db/*_store.py`. Add a simple import-lint test under `tests/` (see §9).

---

## 1. Platform baseline (as analyzed)

**Stack (from `Architecture_Decisions.md` + code):**
- **Frontend:** Next.js 14 App Router + TypeScript + shadcn/ui, deployed on **Vercel**. Pages at `frontend/src/app/<route>/page.tsx`; per-domain API clients at `frontend/src/lib/<domain>-api.ts`; backend base URL from `NEXT_PUBLIC_BACKEND_URL`.
- **Backend:** **FastAPI** (async) in `api/`, deployed on **Railway** via `Dockerfile`. `api/main.py` mounts one router per domain; `SupabaseAuthMiddleware` verifies Supabase JWT on every non-public path and attaches `request.state.user_id` / `access_token`.
- **Business logic:** plain Python packages at repo root (`calc/`, `factors/`, `parsing/`, `llm/`, `rag/`, `gap_analyzer/`, `copilot/`) with a **strict rule: no UI imports, runnable from a plain script**. Routes import business logic; business logic never imports routes.
- **Data:** **Supabase Postgres** with **Row-Level Security**. Migrations are sequential SQL files in `supabase/migrations/` (latest `029_ef_overrides.sql`). Stores in `db/*_store.py` use `get_user_client(access_token)` so RLS applies via the caller's JWT. A `get_service_client()` exists for admin/RLS-bypass (use sparingly).
- **Agents:** LangGraph StateGraphs in `api/graphs/` + a chat agent in `api/agent/`; LangSmith tracing.

**Reference exemplars to copy patterns from:**
- Route: `api/routes/scenarios.py` (CRUD, `Depends(get_current_user)`, `HTTPException`, DTO responses).
- Store: `db/scenario_store.py` + `db/client.py` (user-scoped client, RLS).
- Migration: `supabase/migrations/023_scenarios.sql` (table + indexes + `ENABLE ROW LEVEL SECURITY` + per-op policies on `auth.uid() = user_id`).
- DTOs: `api/models/schemas.py` (Pydantic with `from_row` classmethods).
- Frontend client: `frontend/src/lib/api.ts` (typed fetch against `NEXT_PUBLIC_BACKEND_URL` with Supabase bearer token).
- Nav: `frontend/src/components/app-shell.tsx` `navItems` array.

> **Tenancy note:** existing tables key on `user_id = auth.uid()`, with an org layer added later (migrations `010`, `017`, `019`). Scope 2's customers are multi-site companies with multiple staff (the "Data Wrangler" persona), so Scope 2 tables should carry **both `user_id` and `org_id`** from day one and write RLS policies against **org membership** (reuse the `org_members` pattern from `017_org_data_visibility.sql`), not just the creating user. This is the one place to look at the existing org model — for the RLS pattern only, not to couple data.

---

## 2. Target module layout

```
# ── Backend business logic (net-new, no UI imports, no cross-scope imports) ──
s2_ingestion/          # utility bill ingestion: aggregator pull, CSV import, PDF/OCR, unit normalization, dedup/true-up
    __init__.py
    aggregator.py      # Arcadia / UtilityAPI (Green Button) client adapter(s) behind one interface
    csv_import.py      # guided column-mapping + validation
    ocr.py             # PDF bill extraction via Claude (vision) + low-confidence review queue
    normalize.py       # kWh/therms/CCF/lbs-steam/ton-hr → canonical MWh, with conversion audit record
    dedup.py           # estimated-read flagging + actual/true-up replacement (no double count)
s2_sites/              # site master, templates, boundary, geo→factor-region mapping
    __init__.py
    templates.py       # retail/grocery/F&B/CPG/apparel-DC/office prebuilt templates
    boundary.py        # operational-control default; franchise exclusion → Scope 3 note; lease classification
    geomap.py          # ZIP → eGRID subregion; country → IEA
s2_factors/            # grid emission-factor library, versioned
    __init__.py
    library.py         # eGRID subregions, IEA countries, Green-e (US) + AIB (EU) residual mix, steam/heat
    versioning.py      # pin factor vintage to reporting period; new-vintage alerts
s2_calc/               # dual-method calculation engine
    __init__.py
    location_based.py  # consumption × grid-average factor
    market_based.py    # sourcing hierarchy: supplier-specific → green tariff → residual → grid (flagged)
    instruments.py     # EAC/REC tracking + 8 GHG Protocol quality-criteria checks
    proration.py       # irregular billing periods → reporting year
    engine.py          # orchestrates per-site + rollup; emits two labeled totals (never merged)
s2_quality/            # data-completeness / coverage scoring
    __init__.py
    scoring.py         # actual vs landlord vs benchmark vs estimate; missing bills; estimated reads
s2_reporting/          # "one number, many formats" exports
    __init__.py
    cdp.py             # CDP Supply Chain / Climate C6 mapping
    buyer_templates.py # Walmart / Amazon / EcoVadis field-set mappings (config-driven, not hardcoded)
    summary.py         # standard LB vs MB PDF/CSV export

# ── API layer (net-new routers, all paths under /api/scope2/...) ──
api/routes/scope2_sites.py
api/routes/scope2_ingestion.py
api/routes/scope2_landlord.py       # leased-site data-request workflow
api/routes/scope2_calc.py
api/routes/scope2_reports.py
api/routes/scope2_audit.py
api/models/scope2_schemas.py         # Pydantic DTOs for all of the above (kept separate from schemas.py)

# ── Persistence (net-new stores; all tables prefixed s2_) ──
db/s2_site_store.py
db/s2_bill_store.py
db/s2_landlord_store.py
db/s2_factor_store.py
db/s2_instrument_store.py
db/s2_calc_store.py
db/s2_audit_store.py

# ── Migrations (append-only from 030) ──
# Migration range 040-049 is RESERVED for Scope 2. Scope 1 occupies 030-039
# (feature/scope1-mvp-phase1 already ships 030_s1_* .. 036_s1_rls). Do NOT number
# any Scope 2 migration below 040 — it would collide with Scope 1 at merge time.
supabase/migrations/040_s2_sites.sql
supabase/migrations/041_s2_utility_accounts_bills.sql
supabase/migrations/042_s2_factor_library.sql
supabase/migrations/043_s2_landlord_requests.sql
supabase/migrations/044_s2_instruments.sql
supabase/migrations/045_s2_calculations.sql
supabase/migrations/046_s2_audit_log.sql
supabase/migrations/047_s2_rls_policies.sql   # or inline per-table like 023/024

# ── Frontend (net-new routes + one nav entry) ──
frontend/src/app/scope-2/page.tsx                 # Scope 2 dashboard (coverage + LB/MB summary)
frontend/src/app/scope-2/onboarding/page.tsx      # company → sites → connect utilities
frontend/src/app/scope-2/sites/page.tsx           # site master + data-coverage table
frontend/src/app/scope-2/sites/[siteId]/page.tsx  # site detail: bills, classification, requests
frontend/src/app/scope-2/landlord/page.tsx        # leased-site request queue
frontend/src/app/scope-2/calculate/page.tsx       # run + review LB/MB, flags
frontend/src/app/scope-2/reports/page.tsx         # buyer/CDP response generation + request queue
frontend/src/app/scope-2/audit/[recordId]/page.tsx# trace any number → source
frontend/src/lib/scope2-api.ts                    # typed client for /api/scope2/*
frontend/src/components/scope2/*                   # Scope 2-specific components
```

Dependency direction within Scope 2 (enforced like the platform's existing rules):
`s2_ingestion → normalize/units` (leaf) · `s2_factors` (leaf) · `s2_sites → geomap` (leaf) · `s2_calc → s2_factors + s2_sites` · `s2_quality → s2_sites + s2_ingestion` · `s2_reporting → s2_calc + s2_quality`. Routers import the `s2_*` packages; `s2_*` packages import nothing from `api/` or `frontend/`.

---

## 3. Data model (Supabase, all tables `s2_`-prefixed, org-scoped RLS)

Designed for **audit immutability** and **future hourly/interval + Scope 1/3** (PRD §7 extensibility) — bill data is stored as time-stamped consumption records keyed to a canonical unit, so an interval-data table can later hang off the same account without restructuring.

**Core tables (columns abbreviated):**

- `s2_sites` — `site_id PK, org_id, user_id, name, site_type (enum: retail/grocery/food_service/manufacturing/warehouse_dc/office), address, zip, country, egrid_subregion, iea_country, ownership (owned/tenant_metered/landlord_metered/sub_metered), lease_type (gross/nnn/modified), franchise_flag bool, consolidation_approach, status (active/inactive/seasonal), created_at`. Franchise sites excluded from Scope 2 by the calc engine (routed to a Scope 3 Cat 14 note field).
- `s2_utility_accounts` — `account_id PK, site_id FK, org_id, utility_name, account_number, service_address, energy_carrier (electricity/steam/heat/cooling), source_type (aggregator/csv/pdf/manual), tariff_code, active bool`.
- `s2_utility_bills` — `bill_id PK, account_id FK, org_id, period_start, period_end, raw_quantity, raw_unit, canonical_mwh, cost_usd, is_estimated_read bool, is_cost_only bool, conversion_note, ingestion_method, source_ref (doc/file id), confidence, superseded_by_bill_id (true-up), created_at`. **Immutable**: corrections insert a new row and set `superseded_by_bill_id`; never UPDATE consumption.
- `s2_factor_library` — `factor_id PK, factor_type (egrid/iea/greene_residual/aib_residual/steam), region_code, vintage_year, publish_year, kg_co2e_per_mwh, gwp_set (AR6 GWP-100), source_citation`. Global/reference data (service-role writes; read-only to users). Pinned per reporting period.
- `s2_landlord_requests` — `request_id PK, site_id FK, org_id, landlord_contact, method (email/portal), status (draft/sent/responded/declined/overdue), sent_at, responded_at, reminder_cadence, returned_data_ref, notes`. Contacts/history persist across staff turnover (institutional-knowledge fix).
- `s2_instruments` — `instrument_id PK, org_id, serial_registry_id, instrument_type (rec/go/green_tariff/ppa), vintage, geography_market, mwh, retirement_date, retirement_confirmation, bundled bool, quality_checks JSONB (8-criteria pass/fail), excluded bool`.
- `s2_calculations` — `calc_id PK, org_id, reporting_period, scope (site/entity), site_id nullable, location_based_kg_co2e, market_based_kg_co2e, factor_versions JSONB, inputs_hash, methodology_notes, created_at, created_by`. **Versioned**: recalculation writes a new `calc_id`; published numbers never mutate.
- `s2_audit_log` — `audit_id PK, org_id, entity_type, entity_id, source_ref, factor_source, factor_version, formula, intermediate_values JSONB, actor, approval_status, timestamp`. Every reported tCO2e traces here.
- `s2_data_quality` (or materialized view) — per-site + portfolio coverage score (actual / landlord / benchmark / estimate mix), estimation-coverage %.

**RLS:** each table `ENABLE ROW LEVEL SECURITY`; policies grant `SELECT/INSERT/UPDATE/DELETE` to `authenticated` where the row's `org_id` is in the caller's org membership (pattern from `017_org_data_visibility.sql`), plus `user_id`/`auth.uid()` fallback like `023_scenarios.sql`. `s2_factor_library` is read-to-all-authenticated, write-service-role-only.

---

## 4. Feature → component mapping (PRD §5)

| PRD feature | Backend module(s) | DB table(s) | API router | Frontend |
|---|---|---|---|---|
| 5.1 Multi-site utility ingestion | `s2_ingestion` (aggregator, csv_import, ocr, normalize, dedup) | `s2_utility_accounts`, `s2_utility_bills` | `scope2_ingestion.py` | `/scope-2/onboarding`, `/scope-2/sites/[siteId]` |
| 5.2 Leased-site data workflow | `s2_ingestion.ocr`, `s2_sites.boundary`, benchmark-EUI estimator | `s2_landlord_requests`, `s2_sites` | `scope2_landlord.py` | `/scope-2/landlord` |
| 5.3 Sector site model & boundary | `s2_sites` (templates, boundary, geomap) | `s2_sites` | `scope2_sites.py` | `/scope-2/sites`, onboarding |
| 5.4 Dual-method calc engine | `s2_calc` (location_based, market_based, instruments, proration) + `s2_factors` | `s2_calculations`, `s2_factor_library`, `s2_instruments` | `scope2_calc.py` | `/scope-2/calculate` |
| 5.5 "One number, many formats" reporting | `s2_reporting` (cdp, buyer_templates, summary) | reads `s2_calculations` | `scope2_reports.py` | `/scope-2/reports` |
| 5.6 Audit trail & data-quality scoring | `s2_quality.scoring` + audit writes across modules | `s2_audit_log`, `s2_data_quality` | `scope2_audit.py` | `/scope-2/audit/[recordId]`, dashboard coverage |

**Key flows (PRD §6):** onboarding → gap-fill (landlord/estimate) → calculate → respond → audit map 1:1 to the `/scope-2/*` routes above.

---

## 5. External integrations & build-vs-buy

| Integration | MVP approach | Notes / open decision (PRD §11) |
|---|---|---|
| Utility-data aggregator | Adapter interface in `s2_ingestion/aggregator.py`; start with **one** provider (Arcadia **or** UtilityAPI/Green Button) behind the interface | Multi-aggregator later to widen utility coverage. Credentials tokenized via aggregator OAuth — **never store raw utility passwords** (NFR §7); store tokens encrypted / via aggregator vault. |
| PDF bill OCR | **Claude vision** (`anthropic` SDK, latest Opus 4.8) → structured extract (consumption, period, address, tariff) with a **confidence score**; low-confidence → human-review queue | Build-vs-buy: Claude first (already in stack), evaluate a dedicated OCR vendor only if accuracy insufficient. |
| CSV bulk import | Guided column-mapping wizard; optional Claude-assisted header inference | Validation + preview before commit. |
| eGRID / IEA / residual-mix factors | Seed `s2_factor_library` from published datasets via a `scripts/seed_s2_factors.py` loader (service-role) | Annual vintage refresh must not break historical restatements (NFR §7) — factors pinned per period. |
| Benchmarking-ordinance data | Deferred stub in MVP (NYC LL84 / CA as proxy source) — schema-ready, wire post-MVP | Estimation fallback (floor-area × ENERGY STAR EUI) is the MVP path when no actual data. |

---

## 6. Phased build sequence (maps to PRD §9 milestones M0–M3)

**Phase 0 — Scaffolding & isolation harness (before M0). ✅ COMPLETE (2026-07-05).**
- Done: `s2_*` package skeletons (`normalize.py` + `templates.py` real, rest documented stubs); `api/models/scope2_schemas.py`; `api/routes/scope2_sites.py` (`/api/scope2/health` + `/api/scope2/site-templates`) wired additively into `api/main.py`; `frontend/src/lib/scope2-api.ts`; `/scope-2` shell page; feature-flagged nav entry (`NEXT_PUBLIC_SCOPE2_ENABLED`); `tests/test_scope2_isolation.py` (AST import-lint) + `tests/test_scope2_scaffold.py` (11 tests).
- Migration `040_s2_sites.sql` written (org-scoped RLS via `shares_org_with`). **NOT YET APPLIED** — must run against a **Supabase branch DB** first (CLAUDE.md rule). Numbered `040` because Scope 1 reserves `030–039` (see migration-range note in Section 2).
- Verified: full `pytest` 154 passed; Scope 2 files ruff-clean; `next build` + `next lint` clean; `/scope-2` compiles. (Pre-existing 84 ruff errors in legacy test files are inherited from `main`, out of scope.)

**Phase M0 (wk 0–4) — Data model + calc core.** PRD §9 M0.
- Migrations `040`–`042`, `045`–`046`. Seed `s2_factor_library` (eGRID + IEA + residual mix). Site templates + geo→region mapping. CSV import + unit normalization. Dual-method engine (location + market-based) with proration. Audit log writes.
- Exit / acceptance (PRD 5.4): test portfolio reconciles LB & MB to hand-calculated values; every number traces to `s2_audit_log`.

**Phase M1 (wk 4–8) — Automated ingestion + audit.** PRD §9 M1.
- Aggregator adapter (one provider — **specific provider deferred**; keep the `aggregator.py` interface abstract and pick Arcadia vs UtilityAPI once a design partner's utilities are known). PDF/OCR fallback + review queue, estimated-read/true-up dedup, full audit trail on ingested data.
- Exit (PRD 5.1): ≥80% of a pilot's sites ingested via automation/bulk within 2 weeks of handoff; every datum carries source + period + normalized value + conversion trail.

**Phase M2 (wk 8–12) — Leased-site workflow + quality scoring.** PRD §9 M2.
- Site classification, landlord data-request workflow (templated outreach, status tracking, reminders, structured intake), documented estimation fallback, portfolio data-quality/coverage score.
- Exit (PRD 5.2): every leased site resolves to {actual, landlord-provided, benchmark-proxy, documented-estimate}; estimates audit-labeled with method + inputs; coverage score surfaced.

**Phase M3 (wk 12–16) — Reporting + pilots.** PRD §9 M3.
- **Decision (2026-07-05):** report build order = **CDP Supply Chain → Amazon Supply Chain template → fast-follow Walmart/EcoVadis by pilot mix.** CDP is the aggregator that covers 380+ buyers automatically; Amazon is the first *direct-buyer* template because it **requires both location- and market-based** Scope 2 — exercising the dual-method wedge. Mappings are config/data, so switching the first direct buyer to Walmart (if pilots are Walmart-primary) is a config change, not code. Revisit against actual design-partner mix at M3.
- CDP Supply Chain export + Amazon buyer template (config-driven), inbound request queue with deadlines/status, standard LB/MB PDF/CSV. Turn feature flag on for design-partner orgs.
- Exit / GA gate (PRD §9): ≥3 pilots hit the 30-day defensible-number bar and generate a real buyer/CDP response from one dataset.

---

## 7. Non-functional requirements (PRD §7) → how the platform delivers them

- **Time-to-value ≤30 days, no mandatory PS:** self-service onboarding + templates; no code required per customer.
- **Security:** reuse Supabase Auth + RLS (org-scoped). Utility creds tokenized via aggregator, never stored raw; secrets via env only (CLAUDE.md rule). SOC 2 roadmap inherits the platform posture.
- **Auditability:** immutable `s2_utility_bills` (supersede, don't update) + versioned `s2_calculations` + `s2_audit_log`. Mirrors the platform's existing "published version is immutable; recalc = new version" invariant.
- **Scalability:** 1,000+ accounts/customer — Postgres indexes on `org_id`, `site_id`, `account_id`, `period_start`; ingestion is async (FastAPI async + background jobs for aggregator polls/OCR).
- **Extensibility (hourly + Scope 1/3):** consumption stored as period-keyed canonical-MWh rows → an interval table attaches without migration; `s2_factor_library.factor_type` and `scope` fields leave room for future scopes. Explicitly **do not build** hourly matching now (PRD non-goal), just don't preclude it.

---

## 8. Isolation verification (how we prove "untied from Carbon OS")

1. **Static:** import-lint test fails the build if any `s2_*` / `scope2_*` file imports a Carbon OS business module or non-`s2` store.
2. **Data:** no Scope 2 table has a FK to a Carbon OS table; no Scope 2 store calls a Carbon OS store.
3. **Runtime:** the only shared runtime objects are `get_current_user`, `get_user_client`, the shadcn UI kit, and the FastAPI app instance / Next.js build — infra, not domain.
4. **Navigation:** Scope 2 is reachable only via its own `/scope-2` route tree; no Carbon OS page links into Scope 2 data and vice versa.

Result: Scope 2 can be feature-flagged on/off, developed, tested, and (later) extracted or merged without disturbing any Carbon OS function.

---

## 9. Testing, evals, CI

- **Unit (pytest):** unit normalization table (kWh/therms/CCF/steam → MWh, MBtu vs MMBtu guard); dual-method engine reconciles to golden values; 8-criteria EAC checks; market-based sourcing-hierarchy enforcement (can't drop a tier when a higher one exists); franchise exclusion.
- **Eval invariants (new, Scope 2):** LB and MB totals are two distinct stored numbers, never merged; every reported tCO2e traces to `s2_audit_log`; each market-based instrument shows pass/fail on all 8 criteria; a published `s2_calculations` row never changes (recalc → new row); estimated bills are labeled and replaced (not double-counted) on true-up.
- **Isolation test:** the import-lint described in §8.1.
- **Frontend:** Vitest for `scope2-api.ts` mappers; `next build` must pass.
- **CI gate (unchanged pipeline):** ruff + pytest + `next build`; new logic implementing an eval invariant ships with a test (CLAUDE.md rule).

---

## 10. Risks & open technical decisions

| Item | Position for MVP |
|---|---|
| Tenancy: user-only vs org-scoped RLS | **Org-scoped from day one** (multi-staff customers). Reuse `org_members` RLS pattern; do not couple to Carbon OS org *data* semantics beyond the policy shape. |
| Aggregator coverage gaps | CSV + PDF/OCR are **first-class** paths, not fallbacks-in-name (PRD risk table). |
| OCR accuracy | Claude-first; human-review queue makes low confidence safe; revisit dedicated OCR vendor only if measured accuracy is inadequate. |
| Factor vintage refresh vs historical restatement | Factors **pinned per reporting period**; annual refresh adds rows, never rewrites; `s2_calculations` stores `factor_versions`. |
| GHGP 2027 hourly-matching revision | Architect interval-ready schema now; keep market-based **annual** in MVP (PRD non-goal). |
| Buyer/CDP template drift | Export mappings are **config/data, not hardcode** (`buyer_templates.py` driven by mapping files). |
| Where the plan doc lives / when to commit | This doc is on `feature/scope2-mvp`, uncommitted, mirroring `IMPLEMENTATION_PLAN.md`. Commit only when you say so. |

---

## 11. Immediate next actions (Phase 0)

1. Confirm branch strategy for merging Scope 1 vs starting Scope 2 fresh from `main` (done: forked from `main`; Scope 1 WIP preserved in `stash@{0}`).
2. ~~Decide first aggregator / first buyer template.~~ **Resolved 2026-07-05:** aggregator provider **deferred** (interface stays abstract until a design partner's utilities are known); reporting order = **CDP → Amazon → fast-follow Walmart/EcoVadis** (see M3). Both revisited against real design-partner mix.
3. Scaffold `s2_*` packages + empty routers + `/scope-2` shell + import-lint test.
4. Apply migration `040_s2_sites.sql` to a **Supabase branch DB** and verify RLS with two org fixtures.
5. Seed `s2_factor_library` and stand up the dual-method engine against a golden test portfolio (M0 exit).
