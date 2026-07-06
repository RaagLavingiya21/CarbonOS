# Gap Analysis — Executive Summary
### CarbonOS (Product Footprint Analyzer) vs. the Scope 3 Platform Research Blueprint

**Date:** 2026-07-04
**Prepared for:** product enhancement planning
**Framing chosen:** *full-platform aspiration* — CarbonOS is measured against the **entire** 63-unit corporate Scope 3 platform defined by the research, so every unbuilt job surfaces as a gap.

Companion documents:
- `02-coverage-matrix.md` — the unit-by-unit coverage table (63 research units + CarbonOS's beyond-scope assets)
- `03-enhancement-roadmap.md` — the prioritized path from what exists to the full platform

---

## 1. What we compared

| Side | What it is | Source of truth |
|---|---|---|
| **The target ("should do")** | A blueprint for a **corporate Scope 3 platform** for mid-market consumer brands (1,000–10,000 employees, 0–5 person sustainability team). All 15 GHG Protocol categories, four core jobs — **WHY / MEASURE / MANAGE-REDUCE / REPORT-ACT** — decomposed into **63 atomic build units** across an MVP→V1→V2→V3 roadmap. | `research/build-plan.md`, `research/synthesis.md`, `research/tree.md` |
| **What exists (CarbonOS)** | A **product-level Product Carbon Footprint (PCF) platform**: spend-based (Open CEDA 2025), PACT v3-aligned, with a BOM analyzer, footprint lifecycle/versioning, supplier engagement + primary-data loop, PACT export, product scenario modeling, a chat-agent orchestration layer, plus a **Scope 1 calc engine** and a **corporate Cat-1 rollup**. | `product-footprint-analyzer/` (PCF_PLATFORM_DESIGN.md, CLAUDE.md, code) |

---

## 2. The headline finding: right capability, wrong altitude

CarbonOS is not a smaller version of the research platform — it is a **different altitude** of the same domain.

- **The research platform operates at the corporate level:** ingest company-wide ERP/GL spend → classify into 15 categories → produce a company inventory → set corporate SBTi targets → file a corporate disclosure or answer a corporate customer questionnaire.
- **CarbonOS operates at the product level:** ingest one product's BOM → classify materials → produce that product's cradle-to-gate footprint → engage that product's suppliers → publish that product's PACT payload.

Most of what CarbonOS has built is the **right kind of engine pointed at a single product** rather than the whole company. That is the single most important insight in this analysis, because it means a large share of the "gaps" are **re-aiming and aggregation problems, not from-scratch builds.** The spend→factor classifier, the versioned auditable data model, the supplier primary-data loop, the drill-down traceability — these are exactly the primitives the research says are the hard, defensible core. They already exist; they are just scoped to a product.

The research even schedules product-level PCF as **V3** ("Product carbon + decisions"). In effect, **CarbonOS has built the research's V3 differentiator first and skipped the MVP→V2 corporate spine.** The enhancement job is largely to build the corporate backbone *underneath* the product capability that already exists.

---

## 3. Coverage scorecard

Against the 63 research units (see `02-coverage-matrix.md` for the evidence behind each cell):

| Core job | Units | ✅ Have | 🟡 Partial | 🔴 Gap | Read |
|---|---:|---:|---:|---:|---|
| **Shared foundation** | 3 | 0 | 3 | 0 | Product-level version of every foundation piece exists; corporate spine missing. |
| **P.1 — WHY** (drivers, obligations, requests) | 11 | 0 | 3 | 8 | Gap Analyzer covers category scoping/materiality; obligation-diagnosis and inbound customer-request intake are absent. |
| **P.2 — MEASURE** (15-cat inventory) | 17 | 1 | 8 | 8 | Strong product-level measurement + supplier data loop; no corporate ERP/GL spend ingestion or 15-category inventory; Cat 11 absent. |
| **P.3 — MANAGE & REDUCE** (targets, suppliers) | 14 | 1 | 5 | 8 | Hotspots + supplier engagement + product scenarios exist; SBTi/FLAG target-setting and progress/base-year tracking absent. |
| **P.4 — REPORT & ACT** (disclosure, answers) | 21* | 1 | 6 | 8 | Strong methodology/lineage + PACT publish; questionnaire automation and formal disclosure (ESRS/SB253/CDP) absent — an explicit non-goal today. |
| **Totals** | **63** | **~3** | **~25** | **~35** | Roughly **half** of every unit is at least partially served by an existing engine at product altitude; the other half is genuinely unbuilt. |

\* P.4 has 21 research units; a representative subset appears in the matrix. Counts are directional (many units are "partial" precisely because of the altitude mismatch) — treat the shape, not the decimals, as the signal.

**Shape of the result:** roughly **40% of units have a real head-start** (an existing engine to re-aim), and roughly **55% are open gaps**, concentrated in three areas: corporate inventory measurement (P.2 ERP/GL + 15-cat), target-setting & progress (P.3.2/3.3/3.6), and formal disclosure + questionnaire response (P.4.1/4.2).

---

## 4. What CarbonOS already does well (the head-start)

These are the research's hard, defensible primitives — already built, just at product altitude:

1. **A spend→emission-factor classifier** (`factors/ef_lookup.py`, material→EEIO sector matching with confidence). This is the same class of IP the research flags as the make-or-break unit **P.2.2.b** ("highest-leverage classifier — accuracy of whole inventory hinges here"). Today it classifies BOM materials; re-aimed at corporate GL lines it becomes the MVP's core.
2. **A supplier primary-data loop** (`copilot/exception_router.py` `STORE_DATA` → line-item recalculation → PDS). The research calls supplier PCF ingestion **"the data moat"** (P.2.3.c / P.3.4.b). CarbonOS has closed this loop end-to-end.
3. **A versioned, auditable, PACT-aligned data model** with full drill-down (KPI → product → line item → source citation) and immutable published versions. This is exactly the assurance-readiness spine the research wants in P.2.6 / P.4.3.
4. **Data-quality scoring & PDS** (`calc/dqr.py`, Primary Data Share) — the DQ ladder the research puts in P.2.5.
5. **PACT v3 exchange/publish** — CarbonOS is a footprint *publisher*, an output the research under-weights (it appears only inside P.4.2.6 export). This is a genuine strength to keep.

---

## 5. The biggest gaps (what's missing to be "the platform")

In rough order of how load-bearing they are for the research's ICP:

1. **Corporate spend ingestion + 15-category inventory (P.2.2.a / P.2.1 / P.2.2.b at corporate altitude).** CarbonOS ingests product BOMs, not company ERP/GL spend, and produces product footprints, not a 15-category corporate inventory. This is the foundational job (JTBD-2) and the base everything else stacks on.
2. **Inbound customer/retailer request intake + questionnaire response (P.1.2 + P.4.2).** The research's #1 acute pain and wedge ("answer the customer without a data team" — Walmart/Tesco/CDP-SC/EcoVadis). CarbonOS has no inbound-request intake and no questionnaire-answer automation.
3. **Obligation diagnosis & timeline (P.1.1.b–d, P.1.3, P.1.4.b).** The Gap Analyzer scopes *which Scope 3 categories apply*; it does not diagnose *which regulations/thresholds bite and what's due when* (SB253 $1B, CSRD Omnibus, SBTi V2.0 Category A/B).
4. **SBTi / FLAG target-setting & progress tracking (P.3.2 / P.3.3 / P.3.6 / P.4.4).** No target wizard, no coverage math, no FLAG module, no progress-vs-trajectory or base-year recalculation.
5. **Formal disclosure generation (P.4.1 — ESRS E1 / SB253 / IFRS S2, iXBRL).** Explicitly a **non-goal** in CarbonOS today ("does not prepare a regulatory or compliance report").
6. **Category 11 use-phase & the broader non-Cat-1 categories (P.2 Cat 11 module, logistics Cat 4/9, EOL Cat 12).** CarbonOS is Cat-1-centric (purchased goods); the other consumer hotspots are unaddressed.

---

## 6. Beyond-scope assets CarbonOS has that the research did *not* schedule

Worth naming, because they either accelerate the roadmap or represent scope the research chose to exclude:

| Asset | Note |
|---|---|
| **Scope 1 calc engine** (`s1_calc`, `s1_factors`, `s1_consolidation`, `s1_reporting`) | Research is Scope-3-only. A working Scope 1 inventory (stationary/mobile combustion, GWP, gas breakdown, equity/control consolidation) is a real corporate-inventory capability that widens CarbonOS toward a full GHG inventory tool. |
| **Corporate Scope 3 Cat-1 rollup** (`calc/rollup.py`) | Aggregates per-product footprints × annual volume into a corporate Cat-1 total — a genuine first bridge from product PCF up to a corporate inventory line. The seed of the corporate spine the research wants. |
| **Chat-agent orchestration + memory + teams** (`api/agent/`, `PLATFORM_CHAT_AGENT_PLAN.md`) | A conversational driver and multi-tenant/org layer the research assumes but never decomposes. A UX and go-to-market asset. |
| **PACT v3 publish/exchange** | A downstream-customer *share* capability that positions CarbonOS on the supplier side of the data-exchange the research treats mostly as an integration target. |

---

## 7. Strategic recommendation (one paragraph)

CarbonOS should **keep its product-PCF + supplier-data moat as the wedge and build the corporate Scope 3 backbone underneath it**, rather than rebuild anything. The fastest, lowest-risk path re-aims three assets it already owns — the material classifier (→ corporate spend classifier), the Cat-1 rollup (→ full 15-category inventory), and the versioned data model (→ corporate InventoryVersion) — to stand up a spend-based corporate inventory. That unlocks the research's true MVP (JTBD-1 + JTBD-2: *answer the customer + get a defensible baseline*), which the current product cannot do because it has no company-level number and no inbound-request/questionnaire flow. Target-setting, formal disclosure, and Cat-11/use-phase depth follow as later layers. The detailed, dependency-ordered version of this path is in `03-enhancement-roadmap.md`.
