# Gap Analysis — Detailed Coverage Matrix
### CarbonOS vs. the 63-unit Scope 3 Platform Blueprint

**Date:** 2026-07-04
Companion to `01-executive-gap-summary.md` and `03-enhancement-roadmap.md`.

This document walks the research build plan unit-by-unit and records what CarbonOS covers, the evidence (module/file in `product-footprint-analyzer/`), and the gap. Units are grouped by the four core jobs plus the shared foundation, following `research/build-plan.md` and `research/tree.md`.

### Legend

| Status | Meaning |
|---|---|
| ✅ **Have** | Built and directly serves the unit (may be at product altitude — noted). |
| 🟡 **Partial** | A related engine exists but at a different altitude (product vs. corporate), for a different input, or incomplete. The head-start for closing the gap. |
| 🔴 **Gap** | Not present. |

**Altitude note:** the recurring theme is *P = product altitude, C = corporate altitude*. Many 🟡 rows are "the right engine, pointed at one product instead of the whole company." This is called out per row.

---

## Phase 0 — Shared foundation

| Unit | What the research wants | Status | Evidence in CarbonOS | Gap / notes |
|---|---|---|---|---|
| **Shared data model** | Corporate spine: Organization, **SpendRecord**, Supplier, Product/BOM/Material, Packaging, EmissionFactor, EFMapping, EmissionResult, **InventoryVersion**, SupplierPCF, **Target**, Customer, Request | 🟡 | PACT-aligned `products`/`line_items`, `db/org_store.py`, `db/supplier`/`request_store.py`, footprint versions | Has Org, Supplier, Product/BOM, Request, EF. **Missing** SpendRecord, corporate InventoryVersion, Target, Customer(as buyer). Data model is product-centric; needs a corporate inventory entity above products. |
| **P.2.4 EF library management** | Multi-library, versioned, GWP-aware resolution/mapping across USEEIO, EXIOBASE, ecoinvent, DEFRA, EPA, AGRIBALYSE, grid | 🟡 | `factors/ef_lookup.py` (Open CEDA 2025), `factors/material_mapping.py`, `db/ef_override_store.py`; separate EPA library for Scope 1 (`s1_factors/`) | Single spend dataset (CEDA) + override layer + confidence. **Missing** multi-library resolution, GWP/version awareness, activity/process libraries, grid factors (needed for Cat 11). Override mechanism is a good seed. |
| **P.2.6 consolidation / versioning (base engine)** | InventoryVersion + lineage; enforce single/physical base year | 🟡 | Footprint versioning + immutable published versions + `audit_log`, drill-down traceability | Fully built **at product altitude**. **Missing** corporate inventory versioning/lineage and base-year policy. Product versioning pattern is directly reusable. |

---

## P.1 — WHY: understand & prioritize the drivers (11 units)

| Unit | What the research wants | Status | Evidence | Gap / notes |
|---|---|---|---|---|
| **P.1.1.a** company-profile intake | Capture company profile to drive obligation logic | 🟡 | Gap Analyzer `CompanyProfile` (name, size, sector, geography, products) — `gap_analyzer/models.py` | Exists but feeds category scoping, not an obligation engine. Reusable intake. |
| **P.1.1.b** obligation rules engine | Maintained regulatory rules: SB253 ($1B rev), CSRD Omnibus, SBTi V2.0 thresholds, revenue/headcount triggers | 🟡 | `gap_analyzer/tools/assess_reporting_requirements` (RAG over GHG Protocol) | Assesses *which Scope 3 categories apply*, not *which laws/thresholds bite*. No maintained ruleset, no revenue-threshold logic, no dates. |
| **P.1.1.c** ranked obligation & timeline | "What's due when" ranked obligation timeline | 🔴 | — | Absent. Gap Analyzer outputs recommendations, not a regulatory calendar. |
| **P.1.1.d** business-case / why-now | Auto-generated reason-to-act | 🔴 | — | Absent. |
| **P.1.2.a** request signal capture | Intake of **inbound** customer/retailer requests (Walmart/Tesco/CDP-SC/EcoVadis) | 🔴 | `request_store.py` exists but models **outbound** supplier data requests | The research's #1 wedge. CarbonOS's "requests" go the other direction (to suppliers), not from customers. |
| **P.1.2.b** request → task/deadline | Turn a request into tracked tasks/deadlines | 🔴 | — | Absent. |
| **P.1.2.c** handoff to questionnaire (P.4.2.1) | Route captured request into the answer flow | 🔴 | — | Absent (no questionnaire flow to hand off to). |
| **P.1.3.a** SBTi trigger/coverage readiness | Category A/B test, 5%-per-category coverage math | 🔴 | — | Absent. |
| **P.1.3.b** commit → validation timeline | SBTi commit-to-validation tracker | 🔴 | — | Absent. |
| **P.1.4.a** priority/materiality scoring | Score categories by size/influence/risk | 🟡 | `gap_analyzer/tools/assess_materiality` | Materiality scoring of Scope 3 categories exists — good partial for P.1.4.a and P.2.1.b. |
| **P.1.4.b** cascade-exposure detection | Detect that a customer is itself regulated → will cascade the request | 🔴 | — | Absent (novel differentiated signal; research flags data-sourcing risk). |

---

## P.2 — MEASURE: produce a 15-category inventory (17 units incl. Cat 11 module)

| Unit | What the research wants | Status | Evidence | Gap / notes |
|---|---|---|---|---|
| **P.2.1.a** org boundary setup | Corporate consolidation approach (equity/control) | 🟡 | `s1_consolidation/multiplier.py` (equity/control multiplier for Scope 1) | Concept built for Scope 1; not applied to Scope 3. Reusable pattern. |
| **P.2.1.b** relevance screen | Screen which of the 15 categories are relevant | 🟡 | Gap Analyzer `assess_materiality` + `analyze_data_gaps` | Effectively screens category relevance — a genuine partial. |
| **P.2.2.a** ERP/GL ingestion & normalize | Import company-wide spend/GL and normalize | 🔴 | `parsing/bom_parser.py` ingests **product BOMs**, not corporate GL | Different input entirely. BOM parsing skill transfers, but no ERP/GL connector. |
| **P.2.2.b** spend → category/commodity mapping ⭐ | The make-or-break classifier: GL line → GHG category/commodity → EEIO factor | 🟡 | `factors/ef_lookup.py` material→CEDA sector matching + confidence + `material_mapping.py` | **Same class of IP**, applied to BOM materials not GL spend. The single highest-value re-aim in the whole analysis. |
| **P.2.2.c** spend-based calc engine (EEIO) | kg CO₂e = spend × EEIO factor, across categories | ✅(P) | `calc/footprint.py` (spend-based, kg CO₂e/USD) | Exactly this engine — at product line-item altitude. Aggregate up = corporate calc. |
| **P.2.3.a** hotspot deepening prioritization | Rank where to move from spend → activity/supplier data | 🟡 | `calc/` hotspot ID + `copilot/suppliers_list.py` supplier ranking | Product-level hotspotting exists; corporate prioritization not. |
| **P.2.3.b** SKU/BOM → activity calc | Activity-based (physical) calc for deepened SKUs | 🟡 | BOM structure + calc exist, but engine is **spend-based only** (explicit non-goal) | BOM/SKU model present; activity-based EF path deliberately excluded. |
| **P.2.3.c** supplier request & PCF ingestion ⭐ | "The data moat": collect supplier PCFs/primary data into the inventory | ✅(P) | `copilot/exception_router.py` `STORE_DATA` → line-item recalc → PDS; `copilot/parse_response.py` | End-to-end primary-data loop closed at product altitude. A standout strength. |
| **P.2.5** data-quality scoring | DQ score ladder, gap/uncertainty tracking | ✅(P) | `calc/dqr.py`, confidence scores, PDS (`calc/pds.py`) | Built. Product altitude. |
| **P.2.6** inventory consolidation & versioning | (see Phase 0) | 🟡 | Footprint versioning + audit trail | Product altitude; corporate InventoryVersion missing. |
| **Cat 11 module (11.1–11.6)** use-phase | Use-phase emissions (appliances, apparel laundering, food prep), grid/water factors, scenario hook | 🔴 | — | Absent. Research flags this as whitespace, critical for durables/apparel. |
| *(logistics Cat 4/9, EOL Cat 12, other categories)* | Physical/activity calc for non-Cat-1 hotspots | 🔴 | — | CarbonOS is Cat-1-centric (purchased goods). Other categories unaddressed. |

---

## P.3 — MANAGE & REDUCE: cut Scope 3 over time (14 units)

| Unit | What the research wants | Status | Evidence | Gap / notes |
|---|---|---|---|---|
| **P.3.1.a** hotspot computation | Compute hotspots across category × supplier × SKU × material | ✅(P) | `calc/` hotspot identification | Built at product altitude; corporate hotspotting = aggregate. |
| **P.3.1.b** abatement-opportunity ranking | Rank abatement opportunities | 🟡 | Hotspot + supplier ranking | Ranks hotspots/suppliers; no lever-linked abatement ranking. |
| **P.3.2.a/.b/.c** SBTi target wizard | Near-term/net-zero coverage math, absolute vs intensity, V2.0 Category A/B, 5%/category | 🔴 | — | Absent. Research flags version-sensitivity (V1.3.1 vs V2.0). |
| **P.3.3.a/.b** FLAG module | Food/ag FLAG target + no-deforestation | 🔴 | — | Absent. |
| **P.3.4.a** supplier cohorting/campaigns | Program-scale supplier campaigns | 🟡 | `copilot/suppliers_list.py`, `copilot/draft_email.py`, engagements | Single-supplier engagement exists; cohort/campaign orchestration not. |
| **P.3.4.b** PCF collection orchestration | = P.2.3.c at program scale | ✅(P) | `copilot/exception_router.py` primary-data loop | The loop exists; scaling it to a program is the delta. |
| **P.3.4.c** scorecards & supplier-SBT tracking | Supplier scorecards, track supplier SBTs | 🔴 | — | Absent. |
| **P.3.5.a** consumer lever library | Curated consumer decarbonization levers w/ rough abatement/cost | 🔴 | — | Absent. |
| **P.3.5.b** scenario / trajectory modeling | Model reduction trajectories toward a target | 🟡 | `db/scenario_store.py`, `api/routes/scenarios.py` (duplicate baseline, swap material/supplier, compare deltas) | **Product what-if scenarios exist** — a real capability. But it's product design comparison, not corporate target-trajectory modeling. |
| **P.3.5.c** MAC curve | Marginal abatement cost curve | 🔴 | — | Absent. |
| **P.3.6.a** progress tracking vs trajectory | Track inventory vs target trajectory over time | 🔴 | — | Absent (no corporate inventory/target to track yet). |
| **P.3.6.b** base-year recalculation | GHG Protocol base-year recalc policy | 🟡 | Product versioning/recalc pattern | Recalc-on-new-data exists at product altitude; corporate base-year policy not. |

---

## P.4 — REPORT & ACT: disclosures & decisions (21 units — representative subset)

| Unit | What the research wants | Status | Evidence | Gap / notes |
|---|---|---|---|---|
| **P.4.1.a/.b/.c** disclosure report generation | ESRS E1 / SB253 / IFRS S2 output + iXBRL/CARB formats | 🔴 | — | **Explicit non-goal today** ("does not prepare a regulatory or compliance report"). Largest formal-reporting gap. |
| **P.4.2.1** intake & framework detection | Detect which questionnaire/framework an inbound request is | 🔴 | — | Absent. Research flags as a 🔴 classifier — trust-defining. |
| **P.4.2.2** question → datapoint mapping | Map questionnaire questions to inventory datapoints | 🔴 | — | Absent. The make-or-break "join" for the wedge. |
| **P.4.2.3** category relevance-status | Populate per-category relevance/answers | 🟡 | Gap Analyzer category applicability output | Produces category applicability; not wired to a questionnaire. |
| **P.4.2.4** methodology narrative | Generate methodology narrative for an answer | 🟡 | Methodology metadata, citations, `pages/1_Advisor.py` RAG advisor | Has methodology metadata + advisor; not templated into answers. |
| **P.4.2.5** answer assembly & review | Assemble + human-review a questionnaire answer | 🔴 | — | Absent. |
| **P.4.2.6.a/.b/.c** CDP / EcoVadis / retailer / generic export | Export answers to CDP API, EcoVadis, retailer, spreadsheet/PDF | 🟡 | PACT v3 export (`exchange/pact.py`), CSV export, public shares (`api/routes/shares.py`, `public.py`) | Strong **product-footprint** publishing (PACT). But PACT ≠ CDP/EcoVadis questionnaire formats. Different export target. |
| **P.4.2.7** answer library & reuse | Reuse prior answers (compounding moat) | 🔴 | — | Absent. |
| **P.4.3.a** methodology/source docs | Documented methodology + sources | ✅(P) | Source citations everywhere, methodology metadata, eval invariants | Strong. Every number traces to a source citation. |
| **P.4.3.b** data-lineage / audit graph | Assurance-grade lineage graph | ✅(P) | `audit_log`, KPI→product→line→citation drill-down | Strong at product altitude; extend to corporate. |
| **P.4.4.a/.b** target & progress reporting | SBTi validation packaging + progress narrative | 🔴 | — | Absent (depends on P.3.2/P.3.6). |
| **P.4.5.a/.b** green-claim substantiation / compliance flagging | Substantiate claims; flag EmpCo/GCD exposure | 🔴 | — | Absent. Research flags legal sensitivity (EmpCo live 27 Sep 2026). |
| **P.4.6.a** procurement/supplier decision support | Embed carbon in sourcing decisions | 🟡 | Supplier ranking + engagement | Supplier prioritization exists; sourcing decision workflow not. |
| **P.4.6.b** product/portfolio decision support | SKU/product decisions from PCF | ✅(P) | Product PCF + scenarios + hotspots | This is CarbonOS's home turf — the research's V3 differentiator, built. |
| **P.4.6.c** board/investor climate reporting | Board/investor climate report | 🔴 | — | Absent. |

---

## Beyond-scope assets — CarbonOS capabilities the research did not schedule

| Asset | Evidence | Why it matters |
|---|---|---|
| **Scope 1 calc engine** | `s1_calc/` (stationary, mobile, GWP), `s1_factors/` (EPA), `s1_consolidation/` (equity/control), `s1_reporting/` (gas breakdown CO₂/CH₄/N₂O/SF₆/NF₃, biogenic separated) | Research is Scope-3-only. A working Scope 1 inventory widens CarbonOS toward a full corporate GHG inventory — and the consolidation multiplier is reusable for Scope 3 boundary (P.2.1.a). |
| **Corporate Scope 3 Cat-1 rollup** | `calc/rollup.py`, `db/rollup_store.py`, `api/routes/rollup.py` (Σ per-unit × annual volume) | The **first bridge from product PCF up to a corporate inventory line**. The literal seed of the corporate spine the research wants. |
| **Chat-agent orchestration + memory + teams** | `api/agent/`, `api/skills/`, `PLATFORM_CHAT_AGENT_PLAN.md` | A conversational driver + multi-tenant/org layer the research assumes but never decomposes. UX/GTM asset. |
| **PACT v3 publish/exchange** | `exchange/pact.py`, `api/routes/public.py`, `shares.py` | Positions CarbonOS as a footprint *publisher* on the supplier side of value-chain data exchange — an output the research treats mostly as an integration target. |

---

## Tally

| Bucket | ✅ Have | 🟡 Partial (head-start) | 🔴 Gap |
|---|---:|---:|---:|
| Foundation (3) | 0 | 3 | 0 |
| P.1 WHY (11) | 0 | 3 | 8 |
| P.2 MEASURE (17) | 1 | 8 | 8 |
| P.3 MANAGE/REDUCE (14) | 1 | 5 | 8 |
| P.4 REPORT/ACT (21) | 1 | 6 | 8* |
| **~Total (63)** | **~3** | **~25** | **~35** |

\* Representative subset shown for P.4; remaining units fold into the same 🔴 disclosure/target reporting cluster. Counts are directional — the point is the **shape**: ~40% has a reusable head-start, ~55% is open gap, and the gaps cluster in corporate inventory (P.2), targets/progress (P.3), and disclosure/questionnaire (P.1.2+P.4).

⭐ = the two units the research flags as make-or-break classifiers (P.2.2.b, P.4.2.1/.2). CarbonOS already owns the technology for one of them (P.2.2.b) at product altitude.
