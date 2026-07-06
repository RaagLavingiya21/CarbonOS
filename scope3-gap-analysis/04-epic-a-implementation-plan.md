# Implementation Plan — Epic A: Corporate 15-Category Scope 3 Inventory Backbone

**Branch:** `feature/scope3-mvp`
**Status:** Plan, pre-implementation
**Source:** `03-enhancement-roadmap.md` Epic A (Big bet 1). Grounded in the current `origin/main` codebase.

> **What this epic is.** A company-level, spend-based, 15-category Scope 3 inventory that sits *above* products — the corporate backbone CarbonOS is missing. It reuses the engines CarbonOS already owns (the material classifier, the spend calc, footprint versioning, the Cat-1 rollup) and adds a corporate layer on top. It unlocks the research's foundational job **JTBD-2 ("get a defensible number cheaply")** and produces the single company number that Epic B (questionnaire response) and Epic C (obligations/targets) both require.

> **What this epic is NOT.** Not activity-based (the engine stays spend-based — Open CEDA 2025 kg CO₂e/USD — consistent with CarbonOS's standing decision). Not use-phase/Cat 11 depth (that's Epic H). Not disclosure formatting (Epic G). Cat 1 is *reconciled* with the existing product-PCF rollup, not rebuilt.

Research units closed: **P.2.2.a** (ERP/GL ingestion), **P.2.2.b** (spend→category/commodity classifier, corporate altitude — the make-or-break unit), **P.2.2.c** (spend calc, corporate), **P.2.1.a** (org boundary), **P.2.1.b** (category relevance screen), **P.2.6** (corporate inventory versioning), and the **SpendRecord + InventoryVersion** parts of the shared data model.

---

## 1. Conceptual model

Two sources of Scope 3 data must coexist and **reconcile without double-counting**:

| Source | Altitude | Covers | Quality | Status |
|---|---|---|---|---|
| **Corporate spend-based inventory** (new) | Company | All spend-addressable categories (esp. 1, 2, 4, 5, 6, 7) | Screening-grade | Build in this epic |
| **Product-PCF rollup** (exists) | Product → Cat 1 | Category 1 bottom-up | Higher (has primary data / PDS) | `calc/rollup.py` today |

**The "screen then deepen" rule (from `research/synthesis.md`):** spend-based gives a fast, complete first pass across all 15 categories; where richer data exists (the product-PCF rollup for Cat 1, later activity data for hotspots), the corporate inventory **replaces** the spend estimate for that category and records which method was used. Cat 1 total therefore comes from the product rollup when products exist, else from spend — never both.

```
GL / ERP spend  ──►  classify each line  ──►  category totals (spend-based, all 15)
   (SpendRecord)      (Scope 3 cat +           │
                       EEIO sector + EF)        ▼
                                        reconcile Cat 1 ◄── product-PCF rollup (calc/rollup.py)
                                                │
                                                ▼
                                        InventoryVersion (lock, version, audit) ──► the company number
```

---

## 2. New data model (migrations `050`–`053`)

Follows the existing migration conventions (`supabase/migrations/`, `BIGSERIAL` PKs, RLS with `is_org_member(org_id)`, org visibility mirroring `product_volumes` in `028`).

| Table | Purpose | Key columns |
|---|---|---|
| `inventory_versions` | A corporate Scope 3 inventory snapshot | `inventory_id`, `org_id`, `user_id`, `reporting_year`, `boundary_approach` (`equity`/`operational_control`/`financial_control`), `status` (`draft`/`calculated`/`locked`), `is_base_year` (bool), `total_kg_co2e`, `version`, `created_at`, `locked_at` |
| `spend_records` | Raw normalized GL/ERP line | `spend_record_id`, `inventory_id`, `gl_account`, `description`, `vendor`, `amount_usd`, `currency`, `period`, `source_file`, `flag_status` |
| `spend_classifications` | Classifier output per spend line (separate table so re-classification is versionable) | `classification_id`, `spend_record_id`, `scope3_category` (1–15), `eeio_sector_code`, `eeio_sector_name`, `ef_kg_co2e_per_usd`, `kg_co2e`, `confidence_score`, `data_source`, `is_override`, `flag_status`, `ef_source` |
| `inventory_category_results` | Per-category rollup for a version | `result_id`, `inventory_id`, `scope3_category`, `method` (`spend`/`product_rollup`/`activity`), `total_kg_co2e`, `line_count`, `notes` |

Reuse the boundary concept from `s1_consolidation/multiplier.py` (equity/control multiplier) for `boundary_approach`. MVP may assume a single 100%-owned entity and defer subsidiary structure — **flag as a known limitation**, don't block.

---

## 3. New / extended modules (business logic — no UI imports, per dependency rules)

| Module | New/extend | Responsibility | Reuses |
|---|---|---|---|
| `parsing/spend_parser.py` | **new** | Ingest + normalize GL/ERP CSV; column mapping; apply CLAUDE.md decision rules (missing amount → flag, imperial→metric N/A, duplicates → flag) | mirrors `parsing/bom_parser.py` |
| `factors/spend_classifier.py` | **new** | GL line → (Scope 3 category 1–15, EEIO sector, `EFMatch`) with confidence + alternatives + flag. **The 🔴 make-or-break unit.** | wraps `factors/ef_lookup.py` `lookup_ef` / `lookup_ef_by_sector_code` / `_find_sector` for the sector→EF half; net-new = the GL-line→category step |
| `calc/inventory.py` | **new** | Compute 15-category corporate inventory from classifications; category totals; DQ; **Cat-1 reconciliation** with product rollup | `calc/footprint.py` (kg = usd × ef), `calc/dqr.py` |
| `calc/rollup.py` | **extend** | Generalize `compute_rollup` → category-aware so the product Cat-1 rollup plugs into `inventory_category_results` | existing `compute_rollup`, `db/rollup_store.py` `_latest_published_per_lineage` |
| `db/inventory_store.py` | **new** | CRUD for the 4 new tables; org-scoped reads | `db/store.py`, `db/rollup_store.py`, `db/client.py` `get_user_client`, `is_org_member(org_id)` |

**Key reuse insight (the whole reason this epic is tractable):** `factors/ef_lookup.py` already does fuzzy `material → EEIO sector → EF` matching with confidence scoring and analyst overrides (`lookup_ef_by_sector_code`). A GL line's `description`/`vendor` text is the same kind of input a BOM `material` is. So `spend_classifier` reuses that matcher wholesale for the sector→EF half; the genuinely new work is the **line → Scope 3 category** decision (which of the 15 buckets) and GL-oriented text normalization. Prototype *that* first.

---

## 4. API routes (`api/routes/inventory.py` — thin, orchestrate only)

Mirrors the human-in-the-loop checkpoint pattern already used by the BOM analyzer (parse → review → calculate).

| Endpoint | Method | Does |
|---|---|---|
| `/api/inventory` | POST | Create a draft inventory version (org, year, boundary) |
| `/api/inventory` | GET | List versions for the org |
| `/api/inventory/{id}/spend/import` | POST | Upload GL CSV → `spend_parser` → store `spend_records`; return parse summary + flags |
| `/api/inventory/{id}/classify` | POST | Run `spend_classifier` over records → `spend_classifications`; return per-line category+sector+confidence; low-confidence **flagged for human review** |
| `/api/inventory/{id}/classifications/{rec}` | PATCH | Analyst override of category/sector → recompute that line (reuses `lookup_ef_by_sector_code` override path) |
| `/api/inventory/{id}/calculate` | POST | Compute category totals + reconcile Cat 1 with product rollup → `inventory_category_results` |
| `/api/inventory/{id}/lock` | POST | Lock/version the snapshot (immutable, like a published footprint) |
| `/api/inventory/{id}` | GET | Full inventory: 15 category totals → drill down to spend lines → EF citation |

Register in `api/main.py` alongside existing routers. DTOs as Pydantic models like `api/routes/rollup.py`.

---

## 5. Sub-phases (build in order; each is one testable increment)

Style matches `IMPLEMENTATION_PLAN.md` / `PLATFORM_CHAT_AGENT_PLAN.md`: **Goal · Files · Verify · Prompt.**

### A1 — Data model & store
- **Goal:** The 4 tables exist with RLS; a store layer can CRUD them. No classifier yet.
- **Files:** `supabase/migrations/050_inventory_versions.sql`, `051_spend_records.sql`, `052_spend_classifications.sql`, `053_inventory_category_results.sql` (+ RLS mirroring `028`); `db/inventory_store.py`.
- **Verify:** Run migrations against a **branch** database (never the demo DB — per CLAUDE.md). Create an inventory version, insert spend records, read them back org-scoped. Confirm RLS blocks cross-user reads.
- **Prompt:** *Read `scope3-gap-analysis/04-epic-a-implementation-plan.md` §2 and §3. Create migrations 050–053 for `inventory_versions`, `spend_records`, `spend_classifications`, `inventory_category_results`, following the column specs in §2 and the RLS pattern in `supabase/migrations/028_product_volumes.sql` (owner + `is_org_member(org_id)`). Then create `db/inventory_store.py` with CRUD following `db/rollup_store.py` patterns (`get_user_client`, org-scoped reads). No classifier or calc logic yet.*

### A2 — Spend ingestion
- **Goal:** Upload a GL/ERP CSV, get normalized `spend_records` with flags.
- **Files:** `parsing/spend_parser.py`; `POST /api/inventory/{id}/spend/import` in `api/routes/inventory.py`; a sample GL file in `sample_gl/` for testing.
- **Verify:** Upload a messy GL CSV → rows normalized, missing-amount rows flagged, duplicates flagged (CLAUDE.md decision rules). Determinism: same file → same parse.
- **Prompt:** *Read §3. Create `parsing/spend_parser.py` mirroring `parsing/bom_parser.py` — accept a GL CSV with a column mapping (account, description, vendor, amount, period), normalize, and apply the "Decision Rules for Ambiguous Inputs" from CLAUDE.md (missing amount → flag, duplicates → flag). Wire `POST /api/inventory/{id}/spend/import` to parse and persist via `db/inventory_store.py`. Add a `sample_gl/` example.*

### A3 — The classifier ⭐ (highest risk — de-risk first)
- **Goal:** Each spend line classified to a Scope 3 category + EEIO sector + EF, with confidence and human-review flags.
- **Files:** `factors/spend_classifier.py`; `POST /api/inventory/{id}/classify`; `PATCH …/classifications/{rec}`; a labeled eval set `evals/fixtures/spend_classification_cases.json`.
- **Verify:** **Prototype against the labeled set before wiring the UI** (research's explicit instruction for the 🔴 classifiers). Measure per-category precision. Low-confidence lines flagged. Override path recomputes a line. Determinism (temp 0 / cached).
- **Prompt:** *Read §3 and the reuse insight. Create `factors/spend_classifier.py`: for a GL line, decide the Scope 3 category (1–15), then call `factors/ef_lookup.py` `lookup_ef` for the EEIO sector + EF (reuse its fuzzy matcher and confidence). Return category, sector, `EFMatch`, confidence, flag. Build `evals/fixtures/spend_classification_cases.json` with labeled GL lines and assert per-category accuracy + determinism before building the routes. Wire `POST /classify` and the override `PATCH` (use `lookup_ef_by_sector_code` for overrides).*

### A4 — Category calc + Cat-1 reconciliation
- **Goal:** A full 15-category inventory, with Cat 1 sourced from the product rollup when products exist.
- **Files:** `calc/inventory.py`; extend `calc/rollup.py` (category-aware); `POST /api/inventory/{id}/calculate`.
- **Verify:** Category totals = Σ line contributions; corporate total = Σ categories; Cat 1 equals the product rollup (not spend) when products exist, with provenance recorded and **no double-count**. DQ per category.
- **Prompt:** *Read §1 and §3. Create `calc/inventory.py` computing per-category totals from `spend_classifications` (kg = amount_usd × ef, as `calc/footprint.py`), then reconcile Cat 1: if the org has published product footprints, use `calc/rollup.py`'s product rollup for Cat 1 and mark `method='product_rollup'`; else spend, `method='spend'`. Extend `compute_rollup` to be category-aware. Persist `inventory_category_results`. Wire `POST /calculate`.*

### A5 — Versioning, lock, inventory API, evals
- **Goal:** Lock an immutable inventory version; full drill-down API; enforce invariants.
- **Files:** `POST /api/inventory/{id}/lock`, `GET /api/inventory/{id}`, `GET /api/inventory`; `tests/test_inventory.py`; surface `audit_log`.
- **Verify:** Locking freezes the version; re-classification creates a new version (immutability, mirroring published footprints). `GET` drills KPI → category → spend line → EF citation. All §6 invariants have a passing test.
- **Prompt:** *Read §2 and §6. Add lock/versioning to `inventory_versions` mirroring `products` publish semantics (migration `021_footprint_lineage_and_publish`). Build `GET /api/inventory/{id}` returning the 15 categories with drill-down to spend lines and EF citations. Write `tests/test_inventory.py` asserting every invariant in §6.*

---

## 6. New eval invariants (ship a pytest with each)

- Corporate inventory total = Σ category totals.
- Each category total = Σ line contributions in that category.
- `kg_co2e = amount_usd × ef_kg_co2e_per_usd` for every spend-classified line.
- Every classified line has an `ef_source` citation (extends the existing "every number traceable" invariant to corporate altitude).
- Same spend input → identical classification + totals (determinism).
- Low-confidence / unmapped GL lines are flagged for human review.
- A **locked** inventory version never mutates; re-classification → new version.
- Cat 1 = product rollup when product footprints exist, else spend — **never both** (no double-count); provenance recorded in `method`.

---

## 7. Reuse map (at a glance)

| Need | Reuse | Net-new |
|---|---|---|
| Fuzzy text → EEIO sector → EF + confidence + override | `factors/ef_lookup.py` (`lookup_ef`, `lookup_ef_by_sector_code`, `_find_sector`) | GL line → Scope 3 category (1–15) |
| Spend × EF calc | `calc/footprint.py` formula | Category aggregation |
| Immutable versioned snapshots | `products` version/status + migration `021` | `inventory_versions` |
| Cat-1 bottom-up | `calc/rollup.py`, `db/rollup_store.py` (`_latest_published_per_lineage`) | Reconciliation into category results |
| Boundary (equity/control) | `s1_consolidation/multiplier.py` | Org-level application |
| Ingestion + flagging conventions | `parsing/bom_parser.py`, CLAUDE.md decision rules | GL column mapping |
| DQ scoring | `calc/dqr.py` | Per-category DQ |
| Audit / RLS / org visibility | `audit_log` (003), `is_org_member(org_id)` | — |

---

## 8. Risks & decisions

| Item | Type | Handling |
|---|---|---|
| Classifier per-category accuracy | 🔴 | Prototype `spend_classifier` against a labeled GL set in A3 **before** the UI; confidence threshold + mandatory human review of low-confidence lines. |
| GL/ERP format variety | 🟠 | MVP = generic CSV + column-mapping. Defer NetSuite/QuickBooks/SAP connectors (build-vs-buy: *integrate later*, per research). |
| Category coverage of spend-based | 🟠 | Spend-based naturally covers Cat 1,2,4,5,6,7 (+ parts of others). Cat 11/12/downstream need activity/product data — mark them "screened, deepen later" and hand to **Epic H**. Don't claim false completeness. |
| Boundary/consolidation depth | 🟢 | Reuse the Scope 1 multiplier concept; MVP assumes single entity, subsidiary structure deferred (flagged). |
| Spend-only vs activity engine | ✅ resolved | Epic A is spend-based by design — matches CarbonOS's standing decision. **No blocking decision needed.** |
| Migration safety | 🟢 | Run 050–053 against a branch DB first (CLAUDE.md), never the demo DB. |

---

## 9. Definition of done

A user can: create a FY inventory → upload company GL spend → review/adjust the auto-classification → calculate → get a **locked, versioned, 15-category corporate Scope 3 inventory** where every category total drills down to the spend lines and EF citations behind it, and Cat 1 reconciles with their product footprints. That number is the input Epic B answers customer questionnaires with and Epic C sets targets against.
