# Scope 3 — Working Status / Resume-Here

Living doc. Design lives in `scope3-gap-analysis/` (gap analysis `01–03` + per-epic plans `04–12` + overview `00`); this is the current position + gotchas.
_Last updated: 2026-07-07 · Branch: feature/scope3-v2 (CANONICAL — Epic A frontend + Epics E–I backend merged)_

## 0. STATUS + BLOCKERS (read first — for the integrator)
`feature/scope3-v2` is now the **single canonical Scope 3 branch**: the Epic A frontend and the Epics E–I backend (previously `feature/scope3-v1-backend`) are merged here. All future Scope 3 work happens on this branch, in the `…-scope3` worktree; the backend worktree/branch are retired.

**BLOCKERS / TODO for the integrator:**
- **Migrations `313–317` (E–I) are NOT applied.** `050–059` + `310–312` were hand-applied to the shared dev DB earlier; the new E–I migrations still need applying via the Supabase SQL Editor (idempotent, is_org_member RLS, band `310–319`).
- **The V2 backend DB routes are STATIC-VERIFIED ONLY** (ruff + isolation + migration lint + import smoke). Route→DB→RLS is untested against Postgres until `313–317` are applied.
- **Epic E limitation:** stored `inventory_category_results` has `method` but no `ef_version`, so progress real-vs-method reflects method switches only (constant EF version). Add an `ef_version` column to unlock full EF-version attribution.
- CI note: did NOT touch `ci.yml`. Ships dark behind `NEXT_PUBLIC_SCOPE3_ENABLED`.

## 1. Where we are
Scope 3 is the **corporate 15-category Scope 3 platform** (research blueprint: 9 epics A–I; MVP = A inventory + B questionnaire-answer + C obligations + D targets). **Pure business logic for ALL NINE epics (A–I) is built and tested** across 10 isolated `s3_*` packages (127 scope-3 tests). The **DB layer (migrations + stores + routes) now exists for ALL epics A–I** (code-complete; A/B/C/D + E–I). All **three** 🔴 classifiers (A3 spend→category, B3 framework detection, B4 question→datapoint mapping) are prototyped, hardened, and de-risked against labeled evals. Migrations use two reserved bands: **`050–059`** (A/B/C) and **`310–319`** (D onward: D `310–312`, E–I `313–317`). The **Epic A frontend** exists (`/scope-3` inventory pages). Migrations `050–059`+`310–312` are applied to the shared dev DB; **`313–317` are not yet applied** (see §0). Everything ships dark behind `NEXT_PUBLIC_SCOPE3_ENABLED`.

**`s3_*` packages (10):** `s3_factors` (vendored CEDA) · `s3_measure` (inventory) · `s3_obligations` (C) · `s3_targets` (D) · `s3_questionnaire` (B) · `s3_progress` (E) · `s3_disclosure` (G) · `s3_usephase` (H) · `s3_levers` (I) · `s3_suppliers` (F).

## 2. Done (shipped + post-PR work)
- **Planning:** `scope3-gap-analysis/00–12` — gap analysis + all 9 epic implementation plans + program overview.
- **Vendored engine:** `s3_factors/` (ef_lookup + material_mapping, self-contained CEDA copy) — `d510728`.
- **Epic A — inventory (logic):** `s3_measure/spend_parser.py` (A2), `s3_measure/spend_classifier.py` + `evals/test_spend_classification.py` (A3 🔴, `a1632b2`+`9579953`), `s3_measure/inventory.py` (A4, Cat-1 reconcile).
- **Epic A — DB layer (unapplied):** migrations `050–053` + `db/s3_inventory_store.py` + `api/routes/scope3_inventory.py` — `c7c8f36`, `ff78918`.
- **Epic C — obligations (logic):** `s3_obligations/` engine+ruleset (C2 `e2a3d4e`), business_case (C3) + cascade (C5) `789d062`, sbti_readiness (C4) `772e994`; data `s3_obligations/data/obligation_rules/v2026-07.yaml` + `regulated_buyers.yaml`.
- **Epic C — DB layer (unapplied):** migrations `058–059` + `db/s3_obligation_store.py` + `api/routes/scope3_obligations.py` — `992be65`.
- **Epic D — target math:** `s3_targets/` wizard (trajectory + ambition) + flag — `4d2fd97`.
- **Epic B — framework detector (B3 🔴):** `s3_questionnaire/framework_detector.py` + `evals/test_framework_detection.py` — `ef469a1`.
- **Epic B — question→datapoint mapper (B4 🔴):** `s3_questionnaire/question_mapper.py` + `evals/test_question_mapping.py` — numbers looked-up-only, no-fabrication invariant. *(post-PR-#24)*
- **Epic B — DB layer (unapplied):** migrations `054–057` (requests/questions/mappings/answer_library) + `db/s3_questionnaire_store.py` + `api/routes/scope3_questionnaire.py` (create/list/detect/map/get/submit). *(post-PR-#24)*
- **Epic D — DB layer (unapplied):** migrations `310–312` (s3_targets/target_categories/flag_targets) + `db/s3_target_store.py` + `api/routes/scope3_targets.py` (wizard preview / create+persist / list); reuses `s3_targets` math + `s3_obligations.sbti_readiness` + Epic A inventory + Epic C profile. *(post-PR-#24)*
- **Epic E — progress logic (first mid-term epic):** `s3_progress/` (decompose real-vs-method · tracker on/off-track + base-year recalc · deterministic narrative) + `tests/test_s3_progress.py`. Pure logic; DB layer not yet built. *(post-PR-#24)*
- **Epic G — disclosure logic:** `s3_disclosure/` (versioned `data/frameworks.yaml` for ESRS E1/SB253/IFRS S2 · `mapper.py` inventory→datapoints, numbers looked-up + sourced, SB253 provisional · `serialize.py` CSV/Markdown; iXBRL deferred) + `tests/test_s3_disclosure.py`. Pure logic; DB layer not built. *(post-PR-#24)*
- **Epic H — use-phase logic:** `s3_usephase/` (Cat 11 direct/indirect calc · SAMPLE grid/water factors · sub-sector templates) + `tests/test_s3_usephase.py`. Bounded activity path, method='activity'. Pure logic; DB layer not built. *(post-PR-#24)*
- **Epic I — levers/MAC/claims logic:** `s3_levers/` (lever library + MAC curve + legal-gated claims: substantiate only from primary-data-backed+assured, EmpCo offset-neutrality prohibited) + `tests/test_s3_levers.py`. Pure logic; DB layer not built. *(post-PR-#24)*
- **Epic F — supplier logic:** `s3_suppliers/` (cohorting by emissions/spend + program scorecard; outreach loop is shared copilot, out of scope) + `tests/test_s3_suppliers.py`. Pure logic; DB layer not built. *(post-PR-#24)*
- **Epic B — export packs:** `s3_questionnaire/exporter.py` (CSV + Markdown) + `/export` route. *(post-PR-#24)*
- **Guardrails:** `tests/test_s3_isolation.py` (AST import lint), `tests/test_s3_migrations.py` (SQL-hygiene lint, bands `050–059`+`310–319`). `api/models/scope3_schemas.py` DTOs.
- **Epic A — frontend (v2):** `/scope-3/` hub page · `/scope-3/inventory` list/create · `/scope-3/inventory/[id]` detail with category breakdown · `scope3-api.ts` client · app-shell nav. Gated behind `NEXT_PUBLIC_SCOPE3_ENABLED`. *(v2)*
- **V2 backend — E–I DB layers + disclosure routes (unapplied):** migrations `313` progress · `314` base-year-recalc · `315` suppliers · `316` use-phase-specs · `317` claims; stores `db/s3_{progress,supplier,usephase,claims}_store.py`; routes `api/routes/scope3_{disclosure,progress,suppliers,usephase,levers}.py` (disclosure calc/export · progress track/recalc · supplier CRUD+cohort+scorecard · use-phase calc+specs · levers/MAC/claims-assess). Pure `*_from_rows`/`calc_from_request` helpers make each route unit-testable without a DB. **146 scope-3 tests, ruff + isolation + migration lints clean.** *(v2, merged from feature/scope3-v1-backend)*

## 3. Decisions (+ why)
- **Migration bands (Scope 3):** `050–059` (A `050–053`, B `054–057`, C `058–059`) and **`310–319`** for Epic D onward (D uses `310–312`). The high second band was chosen (integrator) to avoid any collision with the low-numbered scopes; `060–309` intentionally left unused by Scope 3.
- **RLS = `public.is_org_member(org_id)`** (from migration `014`); every table carries `org_id UUID NOT NULL`; `user_id` is `created_by` metadata only, **never in a policy**. (Supersedes the older `shares_org_with(user_id)` pattern.)
- **Vendored the CEDA engine into `s3_factors/`** rather than importing shared `factors/` — hygiene rule 6 forbids importing shared business modules; keeps the module independently mergeable.
- **Spend-based only** for the inventory (Open CEDA 2025, kg CO₂e/USD) — matches CarbonOS's standing decision; activity/use-phase is Epic H.
- **Stores import ONLY `db.client`**; `org_id` is resolved in the route via `db.org_store` and passed down.
- **Trust disciplines (enforced as eval invariants):** numbers looked up never LLM-generated; classifiers are *correct-or-flagged*, never confidently wrong; the obligation ruleset is versioned data with uncertainty first-class (SBTi V2.0 net-zero % stays `unconfirmed`; SB261 stays `uncertain`).
- **Ships dark** behind `NEXT_PUBLIC_SCOPE3_ENABLED`.

## 4. Gotchas & lessons  ← highest value
**Shared (apply to all scopes):**
- CI runs `ruff check --ignore E501` on `evals tests calc parsing factors api llm copilot gap_analyzer rag db observability` — **NOT** `ruff format`, **NOT** the `s*_` module dirs. So E501 never fails CI and module packages aren't lint-gated. (I still keep them ruff-clean locally.)
- `CREATE POLICY` is **not idempotent** — precede each with `DROP POLICY IF EXISTS <name> ON <table>;` so migrations re-run.
- Inserting an explicit `null` **overrides a column DEFAULT** and trips NOT NULL — drop None fields on insert (my stores strip `None`).
- **Migrations are applied BY HAND** (Supabase SQL Editor) to a **shared dev DB all three agents use** — merging code does NOT apply them; prod still needs them separately. **My `050–053`+`058–059` are NOT yet applied anywhere.**
- Reserved bands: Scope 1 = `030–039`, **Scope 3 = `050–059`**, Scope 2 = `040–049`.
- Ships dark via `NEXT_PUBLIC_SCOPE3_ENABLED` until GA.

**Scope-3-specific (cost me time):**
- **Isolation lint import form:** use `import db.s3_x as store`, **not** `from db import s3_x` — the latter reads as a bare-`db` import which isn't on the allow-list and fails `tests/test_s3_isolation.py`. Allowed shared imports: `db.client`, `db.org_store`, `api.middleware.auth`, `api.models.scope3_schemas`, own `s3_*`/`db.s3_*`.
- **`s3_factors` reads the shared `data/Open CEDA 2025 …xlsx`** — that's a read-only DATA dependency, not a code import, so the isolation lint (which checks imports, not file reads) allows it. Don't "fix" it into a code import.
- **YAML 1.1 `yes`/`no` parse as booleans** — bit me on `applies_when_matched: yes` in the ruleset. The loader coerces bool→str; quote or coerce any yes/no token.
- **Three-valued obligation logic:** a missing profile field yields `uncertain`, never a false negative. Model "US-only, no EU" as `eu_turnover_eur=0` (known zero) — leaving it `None` (unknown) makes CSRD resolve `uncertain` instead of `not_applicable`.
- **`build_inventory_from_spend(ParsedSpend)` classifies internally** — it does NOT consume stored classifications. The `/calculate` route reconstructs a `ParsedSpend` from stored `s3_spend_records`. Consequence: per-line classification persistence + line-level drill-down + override PATCH are **deferred** (need A4 to return a record→classification map).
- **SBTi ACA rate (~4.2%/yr) and V2.0 net-zero % are LABELED reference / `unconfirmed`** — never asserted as gospel; verify vs current SBTi text before relying.
- **One driver per worktree:** a stray Cursor window auto-committed A2/A4 in parallel and I nearly duplicated A4 — always `git log` before building; parallelism belongs across worktrees, not within one.
- Run **`pytest tests/test_s3_migrations.py`** after writing any migration — it validates band/`org_id NOT NULL`/`is_org_member`/no-`user_id`-in-RLS/drop-before-create without a DB.

## 5. How to run / test
```bash
# Full module test (pure logic + evals + lints) — no DB, no API key, no network:
python3 -m pytest tests/ evals/test_spend_classification.py evals/test_framework_detection.py -q
# Classifier reports:
python3 -m evals.test_spend_classification
python3 -m evals.test_framework_detection
# Guardrails:
python3 -m pytest tests/test_s3_isolation.py tests/test_s3_migrations.py -q
# Module lint (E501 not CI-gated but kept clean):
python3 -m ruff check s3_factors s3_measure s3_obligations s3_targets s3_questionnaire
```
- **DB:** migrations `050–053`+`058–059` NOT applied. To apply: paste them into the Supabase SQL Editor of the **shared dev DB** (they reference `organizations`/`org_members`/`is_org_member` from `≤029`, already present there). They are re-runnable.
- **Env:** `NEXT_PUBLIC_SCOPE3_ENABLED` (frontend flag, default OFF); backend needs `SUPABASE_URL`/`SUPABASE_ANON_KEY`/`DATABASE_URL` (see `.env.example`). Deps: Python 3.13, `pandas rapidfuzz openpyxl pyyaml supabase fastapi`.

## 6. Next up / deferred
**Queued (v2):**
1. **Apply migrations to the shared dev DB** (by hand, Supabase SQL Editor, in order): the ten `050–059`, then `310`, `311`, `312`. Then **integration-test** the A/B/C/D DB layers (stores, routes, RLS) — currently static-verified only. *(Blocked on DB access — Scope 2 agent applies them; once live, Scope 3 frontend can test end-to-end.)*
2. **Frontend DONE** (v2, this session): `/scope-3/*` pages + `lib/scope3-api.ts`, nav gated behind the flag.
3. **DB layers for E–I:** deferred to later v2 milestone (focus: get A frontending successfully against DB, then expand). See proposal below.
4. Epic B follow-ups: **export packs DONE** (`s3_questionnaire/exporter.py` — CSV + Markdown, `/export` route); still deferred = methodology-narrative assembly (P.4.2.4, needs grounded LLM), PDF export (no `fpdf` in env), structured PDF/xlsx extraction in `detect` (currently UTF-8 text only).
5. Epic A follow-ups (still): per-line classification persistence + line-level drill-down + override PATCH.

**Deferred / parked:**
- Epic A follow-ups: per-line classification persistence, line-level drill-down to EF citation, analyst override PATCH.
- **DB layers for E–I** (progress, disclosure, use-phase, levers, suppliers) — logic done, but tables/stores/routes not built (all in the `310+` band; most only worth wiring after A/B/C/D are applied and real inventories exist).
- Deferred logic bits: Epic B methodology narrative (needs grounded LLM), PDF/iXBRL export (need libs not in env), claims *substantiation* is legal-gated (flagger built, don't ship claims UI without legal review).

## 7. Architectural Decisions & Blockers (v2)

**DB layers for E–I (Epic Progress, Disclosure, Use-Phase, Levers, Suppliers):**
- **Deferred decision:** Should E–I migrations go into `313–319` (second band) or into a new third band (e.g., `320–349`)? Context: Epic D uses `310–312` (3 tables). E–I would need ~10–15 tables total (rough estimate; needs design pass). Decision: **current plan is `313–319`** (remaining slots in the `310s`), but this leaves no buffer. **Flagging for integrator confirmation** — if E–I is MVP post-A/B/C/D, keep `313–319`; if E–I ships v1+, recommend a third band (`320–349`, `060–079`, or `080–099`).
- **Scope:** Initial DB build targets progress tracking (base-year, on/off-track, narrative) and disclosure datapoint mapping (ESRS E1 / SB253 / IFRS S2). Use-phase, levers, suppliers are lower-priority (activity-based, offset claims, supplier outreach all have compliance/legal gates). Recommend MVP = progress + disclosure; v1+ = use-phase/levers/suppliers if there's time.
- **Implementation order:** E (progress) > G (disclosure) > H (use-phase) > I (levers) > F (suppliers). E + G unlock KPI tracking and reporting; H/I/F are value-adds.

**Open questions for Scope 2 integrator:**
- **Which shared dev DB / who applies:** confirm the target dev-DB connection and that Scope 3's `050–059` + `310–312` get applied there (and tracked separately for prod).
- **Per-line classification linkage:** decide whether A4 should return a record→classification map (unlocks drill-down + override) before building Epic A's UI.

**Standards / compliance:**
- **Moving standards:** SBTi V2.0 net-zero coverage % (`unconfirmed`) and SB253 Scope 3 report format (open until CARB final reg ~end-2026) — revisit `s3_obligations/data/` when they land.
