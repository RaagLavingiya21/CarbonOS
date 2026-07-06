# Implementation Plan — Epic H: Category 11 Use-Phase + Category Depth

**Branch:** `feature/scope3-mvp`
**Status:** Plan, pre-implementation
**Source:** `03-enhancement-roadmap.md` Epic H; `00-program-overview.md` §2. Reuses CarbonOS's product-PCF / BOM-SKU depth and the scenario engine; extends the EF library with grid/water factors. **Gated by the spend-only vs. activity decision (§8).**

> **What this epic is.** Deepen measurement beyond spend-based Cat 1 into the other consumer hotspots — above all **Category 11 (use-phase)**, plus activity-based deepening of hotspot SKUs and the logistics (Cat 4/9) and end-of-life (Cat 12) categories. This is CarbonOS's home-turf product depth (the research's V3 differentiator) extended to complete the inventory. It is what SBTi V2.0's per-category ≥5% rule (Epic D) forces for durables/apparel/food brands.

> **What this epic is NOT.** Not a certification-grade LCA engine (no ISO 14067 conformance). Not a replacement for the spend-based baseline — it's the "deepen" half of the research's **"screen then deepen"**: spend-based everywhere, activity-based on the hotspots that matter.

Research units closed: **Cat 11 module 11.1–11.6** (use-phase), **P.2.3.b** (SKU/BOM → activity calc), and activity deepening for **Cat 4/9** (logistics) and **Cat 12** (end-of-life).

---

## 1. The engine-scope decision (read first — it gates the epic)

CarbonOS's stated non-goal is activity-based calculation; the engine is spend-based only. **Cat 11 use-phase is inherently activity-based** (units × lifetime × energy/use × grid factor — there is no spend proxy for "electricity a fridge draws over 10 years"). So Epic H **introduces a bounded activity-based path**, per the research's "screen then deepen":

- The spend-based baseline (Epic A) stays the default for all 15 categories.
- Activity-based calc is applied **only to hotspot SKUs/categories** the analyst chooses to deepen (Cat 11 always; Cat 1/4/9/12 optionally).
- Results are labeled by method (spend vs. activity) and DQ-tagged; the two never silently mix.

**This is a product decision to confirm before building** (§8). Everything downstream in H assumes "yes, a bounded activity path."

Shared discipline: activity results are computed from spec/usage data + bought grid/water factors — looked up, not generated; every result carries its factor citation and DQ tag.

---

## 2. Cat 11 use-phase model (the core of the epic)

Core formula (per `research/cat11-use-phase-specs.md`):

> **Cat 11 (per product) = units sold × expected lifetime × usage intensity × energy/water per use × regional grid/water EF** (+ direct GHG-in-use).

| Sub-unit | Does | Key inputs |
|---|---|---|
| **11.1** Product energy/water spec capture | Capture per-SKU energy/water spec | ENERGY STAR / EU energy label / IEC-ISO test cycles (integrate/scrape); BOM SKU list |
| **11.2** Use-profile & lifetime engine | Usage intensity + lifetime assumptions | sub-sector defaults; user override |
| **11.3** Direct use-phase calc (REQUIRED) | Energy-consuming products (appliances, electronics) | ProductEnergySpec × grid EF |
| **11.4** Indirect use-phase calc (OPTIONAL) | Laundering / hot-water / cooking (apparel, BPC, food) | UseProfile × water-heating/grid EF |
| **11.5** Sub-sector templates | Pre-built durables / apparel / BPC / electronics profiles | default UseProfiles + EF choices |
| **11.6** Use-phase scenario & redesign hook | Feed reduction scenarios (Epic I) + product decisions | 11.3/11.4 results |

---

## 3. New data model (migrations `050`–`052`)

| Table | Purpose | Key columns |
|---|---|---|
| `product_energy_specs` | Per-SKU energy/water spec (11.1) | `product_id`, `energy_per_use`, `water_per_use`, `standby_power`, `spec_source` (ENERGY STAR/label/engineering) |
| `use_profiles` | Usage intensity + lifetime (11.2) | `product_id`, `uses_per_period`, `lifetime_years`, `sub_sector`, `is_default` |
| `activity_results` | Activity-based EmissionResult (11.3/11.4, Cat 4/9/12) | `product_id`, `category_num`, `method` (`activity`), `kg_co2e`, `ef_ref`, `dq_tags`, `direct_or_indirect` |

Extend the EF library (Epic A P.2.4) with **grid/water factors** (IEA, EPA eGRID, DEFRA, AIB) — **BUY**.

---

## 4. New modules (business logic — no UI imports)

| Module | Responsibility | Reuses |
|---|---|---|
| `usephase/spec_capture.py` | 11.1 — capture/import product energy/water specs | BOM/SKU model; integrate ENERGY STAR / EU label data |
| `usephase/use_profile.py` | 11.2 — use-profile & lifetime engine + sub-sector defaults (11.5) | — |
| `usephase/calc.py` | 11.3 direct + 11.4 indirect use-phase calc | EF library (grid/water); `calc/` patterns; `calc/dqr.py` |
| `activity/calc.py` | P.2.3.b activity calc for hotspot SKUs; Cat 4/9 logistics, Cat 12 EOL | BOM model; EF library; Epic A hotspots |
| `usephase/scenario_hook.py` | 11.6 — expose use-phase levers to Epic I | scenario engine (`scenario_store.py`) |
| `db/usephase_store.py` | CRUD | `db/store.py` |

---

## 5. API routes (`api/routes/usephase.py` — orchestrate only)

| Endpoint | Method | Does |
|---|---|---|
| `/api/products/{id}/energy-spec` | POST/GET | Capture/get 11.1 spec |
| `/api/products/{id}/use-profile` | POST/GET | Set/get 11.2 profile (or apply 11.5 template) |
| `/api/products/{id}/usephase/calc` | POST | Compute Cat 11 direct (+ indirect) |
| `/api/products/{id}/activity/calc` | POST | Activity-based calc for a chosen category (Cat 1/4/9/12) |

---

## 6. Sub-phases

### H1 — Spec capture + use-profile engine  (11.1, 11.2, 11.5)
- **Goal:** Per-SKU energy/water specs and use profiles with sub-sector defaults.
- **Verify:** Import an ENERGY STAR spec; apply a durables template; override a lifetime.
- **Prompt:** *Read §1, §2, §3. Create `usephase/spec_capture.py` (import ENERGY STAR / EU-label / engineering specs keyed to BOM SKUs) and `usephase/use_profile.py` (use-profile + lifetime + sub-sector templates for durables/apparel/BPC/electronics). Wire the energy-spec + use-profile routes.*

### H2 — Direct + indirect use-phase calc  (11.3, 11.4)
- **Goal:** Compute Cat 11 direct (required) and indirect (optional) with grid/water factors.
- **Verify:** Direct calc = units × lifetime × energy/use × grid EF; indirect models wash/hot-water/cooking. Method + DQ tagged; location vs. market-based grid choice recorded; standby power handled.
- **Prompt:** *Read §1, §2, and `research/cat11-use-phase-specs.md`. Extend the EF library with bought grid/water factors. Create `usephase/calc.py`: 11.3 direct + 11.4 indirect per the core formula; tag `method=activity`, DQ, and direct/indirect; record grid basis. Wire `/usephase/calc`.*

### H3 — Activity deepening: Cat 1/4/9/12  (P.2.3.b)
- **Goal:** Bounded activity-based calc for chosen hotspot categories.
- **Verify:** A hotspot SKU deepened from spend → activity produces an `activity_result` labeled by method; spend and activity never silently mix in a total.
- **Prompt:** *Read §1. Create `activity/calc.py`: activity-based calc for a chosen category (Cat 1 materials, Cat 4/9 logistics, Cat 12 EOL) on hotspot SKUs; label method; keep spend vs. activity distinct in roll-ups. Wire `/activity/calc`.*

### H4 — Scenario hook + evals  (11.6)
- **Goal:** Expose use-phase levers to Epic I; lock invariants.
- **Verify:** 11.6 feeds the scenario engine; `tests/test_usephase.py` covers §7.
- **Prompt:** *Read §4, §7. Create `usephase/scenario_hook.py` exposing use-phase reduction levers to the scenario engine. Write `tests/test_usephase.py`.*

---

## 7. New eval invariants

- Cat 11 direct calc equals units × lifetime × energy/use × grid EF; every result carries a grid/water EF citation + DQ tag.
- Every activity result is labeled `method=activity`; spend-based and activity-based values never silently combine in a total.
- Indirect use-phase is flagged optional-but-included when reported.
- Grid basis (location vs. market-based) is recorded per result.
- Activity numbers are looked up from spec + bought factors, never LLM-generated.

---

## 8. Risks & decisions

| Item | Type | Handling |
|---|---|---|
| **Spend-only vs. activity path** | decision (gates H) | H introduces a *bounded* activity path (§1). Confirm before building — this is the program's biggest methodology fork. |
| Grid/water + product-spec data sourcing | 🟠 | BUY grid/water factors; integrate/scrape ENERGY STAR / EU-label product data (research build-vs-buy). |
| Grid decarbonization over lifetime | 🟠 | Document current vs. projected grid factor choice; make it explicit, not silent. |
| Not certification-grade LCA | 🟢 | Screening-grade activity calc; no ISO 14067 conformance claim. |
| Depends on product PCF + A | 🟠 | Uses the BOM/SKU model + corporate hotspots to pick what to deepen. |

---

## 9. Definition of done

For a durables/apparel/food SKU, the analyst captures its energy/water spec (or applies a sub-sector template), and the platform computes its **Category 11 use-phase emissions** (direct required, indirect where significant) with grid/water factors and DQ tags — plus **activity-based deepening** of chosen Cat 1/4/9/12 hotspots — all clearly labeled by method and feeding both the corporate inventory's non-Cat-1 categories (satisfying SBTi ≥5% coverage) and the Epic I reduction scenarios. Product depth now completes the inventory.
