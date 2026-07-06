# Scope 3 Platform — Program Overview & Build Sequencing

**Branch:** `feature/scope3-mvp`
**Role:** Top-level map over the whole `scope3-gap-analysis/` bundle. Read this first; it ties the gap analysis, the roadmap, and the per-epic implementation plans into one dependency-ordered build program.

---

## 1. The bundle (reading order)

| Doc | What it answers |
|---|---|
| **00-program-overview.md** *(this)* | The whole program on one screen: epics, dependencies, critical path, sequencing. |
| `01-executive-gap-summary.md` | What CarbonOS is vs. the research blueprint, and the headline finding (right engines, wrong altitude). |
| `02-coverage-matrix.md` | The 63 research units, unit-by-unit: Have / Partial / Gap, with code evidence. |
| `03-enhancement-roadmap.md` | The 9 enhancement epics (A–I) with reuse, effort, and the phased path. |
| `04-epic-a-implementation-plan.md` | **Build-ready:** corporate 15-category inventory backbone. |
| `05-epic-b-implementation-plan.md` | **Build-ready:** inbound request → questionnaire answer. |
| `06-epic-c-implementation-plan.md` | **Build-ready:** driver & obligation front door. |

The one-line thesis carried through all of them: **CarbonOS already owns the hard, defensible product-level engines (spend→factor classifier, supplier primary-data loop, versioned auditable model, PACT publish, Cat-1 rollup); the program builds the corporate Scope 3 backbone *underneath* them — reuse, not rebuild.**

---

## 1b. Scope-3 module conventions (parallel-build hygiene — SUPERSEDES per-plan naming)

This module is built as an isolated lane on `feature/scope3-mvp` alongside Scope 1 and Scope 2, all landing on `main`. **Plans `04`–`12` were written before the hygiene rules and use pre-namespace names; the conventions below govern and override them.**

| Concern | Convention | Note |
|---|---|---|
| **Packages** | `s3_*` only: `s3_factors` (vendored CEDA engine), `s3_measure` (parser/classifier/inventory), `s3_obligations` | No imports of shared business modules (`calc`/`factors`/`parsing`/`gap_analyzer`/`copilot`/`rag`/`exchange`/`llm`) or sibling scopes — enforced by `tests/test_s3_isolation.py`. Where a plan says `factors/ef_lookup.py`, read `s3_factors/ef_lookup.py`. |
| **Stores** | `db/s3_*_store.py` | Plans saying `db/inventory_store.py` → `db/s3_inventory_store.py`, etc. |
| **Routes** | `api/routes/scope3_*.py` | Plans saying `api/routes/questionnaire.py` → `api/routes/scope3_questionnaire.py`. |
| **URLs / API client** | `/scope-3/*` · `lib/scope3-api.ts` | Plans saying `/api/questionnaires` → under `/scope-3`. |
| **DTOs** | `api/models/scope3_schemas.py` | |
| **Feature flag** | `NEXT_PUBLIC_SCOPE3_ENABLED` | Ships **dark** — nav hidden, default OFF in prod. |
| **Migration band** | **`050`–`059`** | MVP fits exactly: Epic A `050`–`053`, Epic B `054`–`057`, Epic C `058`–`059`. Do **not** use `030`/`040` (reserved for S1/S2). **Epics D–I need additional bands coordinated with the integrator — the numbers in plans `07`–`12` are placeholders, not final.** |
| **Tenancy / RLS** | Every org-scoped table carries `org_id UUID NOT NULL`. RLS: `USING (public.is_org_member(org_id))` on SELECT/UPDATE/DELETE, `WITH CHECK (public.is_org_member(org_id))` on INSERT (helper from migration `014`). | `user_id` is optional `created_by` **metadata only — NEVER in an RLS policy**. Precede every `CREATE POLICY` with `DROP POLICY IF EXISTS <name> ON <table>;` so migrations are re-runnable. **Global reference tables** = read-all-authenticated, service-role writes. This supersedes the older `user_id`/`shares_org_with` pattern mentioned in the per-epic plans. |
| **Shared files** | append-only (`api/main.py` include_router, app-shell nav entry, `requirements.txt`) | Never modify shared infra (`auth`, `db/client`, `org_store`, `is_org_member`); a genuine shared change lands as its own PR to `main` first. |

---

## 2. The program on one screen

Effort: S≈days, M≈1–2wk, L≈3–5wk, XL≈6wk+ (one small squad).

| Epic | Name | Serves (JTBD) | Phase | Effort | Depends on | Reuses (existing CarbonOS) | Plan |
|---|---|---|---|---|---|---|---|
| **A** | Corporate 15-cat inventory backbone | JTBD-2 defensible number | Near | XL | — (foundation) | `ef_lookup` classifier, `footprint` calc, versioning, `rollup` | ✅ `04` |
| **B** | Inbound request → questionnaire answer | JTBD-1 answer the customer | Near | L–XL | **A** | `pcf_requests` inbox, gap-analyzer categories, RAG advisor | ✅ `05` |
| **C** | Driver & obligation front door | JTBD-0 is this my problem | Near | M–L | A (only C4) | gap-analyzer `CompanyProfile`+`assess_materiality`, RAG advisor | ✅ `06` |
| **D** | SBTi + FLAG target-setting | JTBD-4 targets accepted | Mid | L | **A** (+ Epic C readiness) | inventory as coverage denominator; Target entity | ✅ `07` |
| **E** | Progress tracking + base-year recalc | JTBD-7 prove it was real | Mid | M–L | A, D | product versioning/recalc, hotspots | ✅ `08` |
| **F** | Supplier engagement at program scale | JTBD-5 move the supply chain | Mid | M | existing copilot loop (+A) | `copilot` primary-data loop, supplier ranking | ✅ `09` |
| **G** | Formal disclosure (ESRS/SB253/iXBRL) | JTBD-6 the one artifact | Long | L–XL | **A** | inventory, `audit_log`/citations lineage, `exchange/` serialize | ✅ `10` |
| **H** | Cat-11 use-phase + category depth | product depth | Long | L | product PCF (+A) | BOM/SKU model, scenario engine | ✅ `11` |
| **I** | Levers / MAC / claims / decisions | JTBD-3 + decisions | Long | L | A, H | product scenario engine, supplier ranking | ✅ `12` |

All nine epics (A–I) now have detailed build-ready plans (`04`–`12`). The program is fully specified end-to-end.

---

## 3. Cross-epic critical path (the dependency spine)

```
        ┌──────────────── Phase 0 (inside A): shared data model + EF library + versioning
        ▼
   A: corporate inventory ──┬──► B: questionnaire answer   ┐
   (XL, 🔴 spend classifier)│    (L–XL, 🔴 detect + map)   ├─► MVP WIN CONDITION
                            │                              ┘   (request → baseline → submitted answer, <2wk)
   C: obligation front door │  (M–L; C1–C3 parallel, C4 needs A)
                            │
                            ├──► D: targets ──► E: progress/recalc
                            ├──► G: formal disclosure
                            └──► H: category depth ──► I: levers/claims

   F: supplier program scale  ── mostly parallel (reuses the existing copilot loop; A sharpens corporate hotspots)
```

- **The MVP is A + B** (with C as the funnel on top). Everything mid/long-term hangs off A's corporate inventory.
- **Three 🔴 classifiers sit on the critical path** and are the schedule risk: A3 (spend→category), B3 (framework detection), B4 (question→datapoint mapping). **Prototype all three against labeled data before their surrounding UI** — this is the research's standing instruction and it's repeated in each plan.
- **C1–C3, F, and H can start in parallel** with A/B — they don't block the MVP and use largely independent code.

---

## 4. Phasing & win conditions

| Phase | Epics | Delivers | Win condition |
|---|---|---|---|
| **Near-term** | A, B, C | The research's true MVP | *A 2-person team goes from a retailer/CDP/EcoVadis request to a submitted, credible answer in <2 weeks, no consultant* (`research/synthesis.md`). |
| **Mid-term** | D, E, F | Annual system of record | Targets set, progress tracked year-over-year, supplier data compounding — the platform becomes the thing they renew. |
| **Long-term** | G, H, I | Full-platform parity + differentiation | Audited disclosure output, product/use-phase depth, and decision/claims support — competes head-on with Watershed/Sweep while keeping the product-PCF moat. |

---

## 5. Cross-cutting engineering concerns (apply across epics)

1. **Prototype the 🔴 classifiers first.** A3, B3, B4 — labeled eval fixtures before UI. Product trust = classifier accuracy.
2. **Numbers are looked up, never generated.** The no-fabrication discipline (Epic B §1, Epic C §1) applies everywhere the LLM touches a figure — extends the existing advisor "no fabricated numbers" rubric to every output. Narrative is generated + grounded; numbers are resolved from datapoints with citations.
3. **Moving standards are data, not code, and staffed.** Three drift surfaces need an ongoing maintenance cadence, not a one-time build: the **obligation ruleset** (C — dated versioned YAML), the **questionnaire framework templates** (B — yearly format drift), and the **disclosure formats** (G — SB253 final reg ~end-2026, ESRS taxonomy). Each records the version it used.
4. **Honest uncertainty.** Where the research says "unconfirmed / in flux" (SBTi V2.0 net-zero %, SB253 Scope 3 format, SB261 injunction, EU GCD suspended), the product surfaces a watch-item — never a fabricated fixed value. Enforced as eval invariants.
5. **Build-vs-buy (from `research/build-plan.md`).** BUY/license the EF datasets and grid factors; INTEGRATE CDP/EcoVadis/ERP connectors and an iXBRL tagging lib; BUY cascade-exposure enrichment data. **BUILD the classifiers** (A3, B3, B4) — that's the defensible IP.
6. **Shared foundation is built once.** The corporate data model (SpendRecord, InventoryVersion, Target, Customer/Request) and the EF library/versioning layer underpin every epic — Epic A stands most of it up; later epics extend, don't duplicate.

---

## 6. Team-shaped sequencing (small squad)

1. **Weeks 1–6:** Epic A foundation — data model + EF library + spend ingestion (A1–A2), and **prototype the A3 spend classifier against a labeled GL set** (the make-or-break). In parallel, start Epic C's independent front-door pieces (C1–C3).
2. **Weeks 6–12:** finish A (calc + Cat-1 reconciliation + lock/versioning, A4–A5) → a working corporate inventory. Begin Epic B and **prototype B3/B4 classifiers**.
3. **Weeks 12–18:** finish B (assembly → export) → ship the MVP: request → baseline → submitted answer. **Win condition met.** Wire C4 (SBTi readiness) onto the now-real inventory.
4. **Mid-term:** D (targets) → E (progress), and scale F (supplier program) off the existing loop.
5. **Long-term:** G (disclosure), H (Cat-11/category depth), then I (levers/MAC/claims — claims last, given EmpCo legal exposure live 27 Sep 2026).

---

## 7. Decisions that gate the program (owner: product)

These are forks the plans deliberately do **not** settle — resolve before the dependent epic:

| Decision | Gates | Note |
|---|---|---|
| Spend-only vs. add an activity-based path | H (and P.2.3.b) | A/B/C are spend-based and unaffected. "Screen then deepen" implies *some* activity path eventually; decide before H. |
| Reverse the "no corporate inventory / no compliance report" non-goals | A, G | Full-platform aspiration requires this; already implicitly accepted by planning A and G. Confirm it's a deliberate GTM move. |
| Green-claims scope | I | EmpCo in force 27 Sep 2026; GCD suspended; FTC 2012. Research says build carefully and last — recommend deferring I's claims features. |
| Standards-currency staffing | C, B, G | Ongoing maintenance headcount for the three drift surfaces (§5.3), not a one-time cost. |

---

## 8. Status

- ✅ Gap analysis complete (`01`–`03`).
- ✅ Near-term MVP trio planned build-ready (`04` A, `05` B, `06` C), committed on `feature/scope3-mvp`.
- ✅ Mid-term layer planned build-ready (`07` D, `08` E, `09` F) — targets, progress, supplier scale.
- ✅ Long-term layer planned build-ready (`10` G, `11` H, `12` I) — disclosure, category depth, levers/claims.
- 🟢 **All nine epics (A–I) are specified.** The program is planning-complete end-to-end.
- 🔜 Next steps are execution, not planning: prototype the three 🔴 classifiers (A3, B3, B4); resolve the §7 gating decisions; begin Epic A. (And the pending `.docx` conversion of gap docs `01`–`03`.)
