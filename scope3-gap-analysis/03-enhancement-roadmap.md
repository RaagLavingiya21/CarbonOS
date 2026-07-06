# Gap Analysis — Enhancement Roadmap
### From product-PCF wedge to full corporate Scope 3 platform

**Date:** 2026-07-04
Companion to `01-executive-gap-summary.md` and `02-coverage-matrix.md`.

This document turns the gaps into a prioritized, dependency-ordered enhancement path. The framing (per the exec summary) is **full-platform aspiration**: the end state is the complete 63-unit corporate Scope 3 platform. The strategy to get there is **build the corporate backbone underneath the product-PCF capability CarbonOS already owns** — reusing engines, not rebuilding.

---

## 1. Prioritization principles

Enhancements are ranked by four factors, in order:

1. **Adjacency / leverage** — does it re-aim an engine CarbonOS already has? (Cheapest, lowest-risk, highest-confidence wins go first.)
2. **JTBD urgency** — does it serve the research's acute wedge jobs (JTBD-1 *answer the customer*, JTBD-2 *cheap defensible inventory*)? These open budgets.
3. **Unblocking power** — how many downstream units does it unblock? (Corporate inventory unblocks targets, disclosure, progress.)
4. **Risk** — regulatory/legal sensitivity and classifier-accuracy risk are pushed later or de-risked early with prototypes.

A note on the altitude theme running through everything: **most near-term value is aggregation and re-aiming, not net-new invention.** The product engines exist; they need a corporate layer above them.

---

## 2. The two big bets

Everything else stacks on these.

- **Big bet 1 — The corporate inventory backbone.** A company-level, spend-based, 15-category inventory sitting *above* products. Reuses the material classifier (P.2.2.b), the spend-based calc (P.2.2.c), the versioned data model (P.2.6), and extends the existing Cat-1 rollup (`calc/rollup.py`) from "Cat 1 only" to "all 15." Without this, CarbonOS has no company number — and targets, disclosure, and questionnaire answers all need one.
- **Big bet 2 — The inbound request → answer loop.** Capture a customer/retailer/CDP/EcoVadis request, map its questions to the inventory, and emit a credible answer. This is the research's #1 wedge and the emotional buying trigger. It depends on Big bet 1 for the numbers to answer with.

CarbonOS already owns the *hard, defensible half* of Big bet 1 (the classifier and the supplier data moat). That is the reason this roadmap is realistic rather than a rewrite.

---

## 3. Enhancement epics (grouped, with reuse and unit coverage)

Each epic lists: the research units it closes, what CarbonOS reuses, the net-new work, and a rough effort (S/M/L/XL per the research's t-shirt scale: S≈days, M≈1–2wk, L≈3–5wk, XL≈6wk+).

### Epic A — Corporate spend ingestion & 15-category inventory  *(Big bet 1)*
- **Closes:** P.2.2.a, P.2.2.b (corporate), P.2.2.c (corporate), P.2.1.a, P.2.1.b, P.2.6 (corporate), Shared data model (SpendRecord, InventoryVersion)
- **Reuses:** `factors/ef_lookup.py` classifier ⭐, `calc/footprint.py` spend calc, `calc/rollup.py` aggregation pattern, footprint versioning, `s1_consolidation/multiplier.py` for boundary
- **Net-new:** ERP/GL connector + normalizer (many formats — 🟠); re-aim the classifier from BOM materials to GL lines; corporate InventoryVersion entity; 15-category mapping/relevance screen
- **Effort:** **XL** (dominated by the ERP ingestion + classifier re-aim; research flags P.2.2.b as the make-or-break — prototype against a labeled GL set first)

### Epic B — Inbound request intake & questionnaire response  *(Big bet 2)*
- **Closes:** P.1.2.a/.b/.c, P.4.2.1, P.4.2.2, P.4.2.3, P.4.2.4, P.4.2.5, P.4.2.6.b/.c, P.4.2.7
- **Reuses:** Gap Analyzer category-applicability output (feeds P.4.2.3), methodology metadata + RAG advisor (feeds P.4.2.4), existing export/serialization patterns (`exchange/`, shares)
- **Net-new:** inbound request model (distinct from the outbound supplier `request_store`); framework-detection classifier (🔴 trust-defining); question→datapoint mapping (🔴 the join); answer assembly + review UI; answer library
- **Effort:** **L–XL** (two classifiers; prototype framework detection early). Depends on Epic A for numbers.

### Epic C — Driver & obligation front door
- **Closes:** P.1.1.b (real rules engine), P.1.1.c, P.1.1.d, P.1.3.a/.b, P.1.4.a, P.1.4.b
- **Reuses:** `CompanyProfile` intake (`gap_analyzer/models.py`), `assess_materiality` (→ P.1.4.a)
- **Net-new:** maintained obligation ruleset (SB253 $1B, CSRD Omnibus, SBTi V2.0 Category A/B, timelines — 🟠 must stay current); SBTi coverage-math; cascade-exposure signal (needs external data — 🔴 sourcing risk)
- **Effort:** **M–L**. Runs in parallel with A/B as the top of the funnel.

### Epic D — Target-setting: SBTi + FLAG
- **Closes:** P.3.2.a/.b/.c, P.3.3.a/.b, P.4.4.a
- **Reuses:** corporate inventory (Epic A) as the coverage denominator; Target entity (added in Epic A)
- **Net-new:** version-aware SBTi wizard (V1.3.1 vs V2.0, 5%/category, absolute vs intensity — 🟠); FLAG module + no-deforestation dates; SBTi validation packaging
- **Effort:** **L**. Depends on Epic A.

### Epic E — Progress tracking & base-year recalculation
- **Closes:** P.3.6.a, P.3.6.b, P.4.4.b, P.3.1.a/.b (corporate)
- **Reuses:** product versioning/recalc pattern, corporate InventoryVersion (Epic A), hotspot computation
- **Net-new:** corporate base-year recalc policy (structural-change thresholds); progress-vs-trajectory tracking; corporate hotspot rollup
- **Effort:** **M–L**. Depends on Epics A + D.

### Epic F — Supplier engagement at program scale
- **Closes:** P.3.4.a, P.3.4.b, P.3.4.c, P.2.3.a (corporate)
- **Reuses:** the **primary-data loop** (`copilot/exception_router.py` `STORE_DATA`) ⭐ — already closed; supplier ranking; email drafting
- **Net-new:** cohorting/campaign orchestration; supplier scorecards; supplier-SBT tracking
- **Effort:** **M** (mostly scaling an existing loop — high-confidence, high-leverage; this is the moat).

### Epic G — Formal disclosure generation
- **Closes:** P.4.1.a/.b/.c, P.4.6.c
- **Reuses:** corporate inventory (Epic A), methodology/lineage (`audit_log`, citations — the assurance spine is largely there)
- **Net-new:** ESRS E1 / SB253 / IFRS S2 datapoint mapping; narrative+quant assembly; iXBRL/CARB output (🔴🟠 SB253 format not final until ~end-2026 — buy an iXBRL tagging lib per the research's build-vs-buy call)
- **Effort:** **L–XL**. Reverses the current explicit non-goal ("does not prepare a regulatory/compliance report"). Depends on Epic A.

### Epic H — Category depth: Cat 11 use-phase + non-Cat-1 categories
- **Closes:** Cat 11 module 11.1–11.6, P.2.3.b (activity), logistics Cat 4/9, EOL Cat 12
- **Reuses:** BOM/SKU model, product PCF depth, scenario engine
- **Net-new:** use-phase calc + grid/water factors (buy); activity-based EF path (a departure from spend-only — decision needed); other-category methods
- **Effort:** **L**. This is where CarbonOS's product depth extends; research schedules it late (V1–V3).

### Epic I — Reduction levers, scenarios, decisions, claims
- **Closes:** P.3.5.a/.b/.c (MAC), P.4.5.a/.b (green claims), P.4.6.a/.b
- **Reuses:** **product scenario engine** (`api/routes/scenarios.py`) ⭐ — extend from product what-ifs to corporate trajectories; supplier ranking for procurement decisions
- **Net-new:** consumer lever library; corporate trajectory modeling; MAC curve; green-claim substantiation (🔴 legal — EmpCo live 27 Sep 2026, GCD status uncertain — build carefully/last)
- **Effort:** **L**. Green-claims is legally sensitive; defer per the research.

---

## 4. Phased sequence

Aligned to the research's own MVP→V1→V2→V3 ordering, but re-sequenced to exploit CarbonOS's head-start.

```
NOW (built)         NEAR-TERM              MID-TERM               LONG-TERM
─────────           ─────────              ────────               ─────────
Product PCF     →   Epic A: corporate  →   Epic D: targets    →   Epic G: formal
Supplier loop       inventory backbone     (SBTi/FLAG)            disclosure (ESRS/
Scenarios           Epic B: request →      Epic E: progress /     SB253/iXBRL)
PACT publish        answer loop            base-year recalc      Epic H: Cat 11 +
Scope 1             Epic C: obligation     Epic F: supplier          category depth
Cat-1 rollup        front door             program scale         Epic I: levers/MAC/
Chat agent                                                          claims/decisions
```

- **Near-term (unlocks the research's true MVP — JTBD-1 + JTBD-2):** Epics A, B, C. Win condition (from `research/synthesis.md`): *a 2-person team goes from a retailer request to a credible submitted answer in <2 weeks, no consultant.* CarbonOS cannot do this today because it has no company number and no inbound-request flow — these three epics fix exactly that, on top of engines that already exist.
- **Mid-term (JTBD-3/4/5/7):** Epics D, E, F — targets, progress, and scaling the supplier moat. Turns the tool into the annual system of record.
- **Long-term (JTBD-6 + product depth):** Epics G, H, I — formal audited disclosure, category depth, and decision/claims support.

**Prototype-first risks to pull forward:** the two 🔴 classifiers (Epic A's re-aimed spend classifier, Epic B's framework-detection + question-mapping) are the schedule risk. Per the research, prototype both against labeled datasets before committing the surrounding build.

---

## 5. Decisions the team must make (not just build)

These are forks the roadmap can't settle unilaterally:

1. **Spend-only vs. activity-based engine.** CarbonOS's stated non-goal is activity-based calc. Epic H (Cat 11, deepened SKUs) and the research's P.2.3.b assume some activity-based path. Decide whether to hold spend-only (screening-grade, honest) or add a hybrid path. The research recommends "screen then deepen" (spend first, activity on hotspots).
2. **How far up-altitude to go.** Full-platform aspiration means becoming a corporate inventory + disclosure tool, competing with Watershed/Sweep/Normative — not just the product-PCF niche. Confirm the ambition matches GTM.
3. **Reverse the "no compliance report" non-goal?** Epic G directly contradicts CarbonOS's current non-goal. Formal disclosure (ESRS/SB253) is a large, standards-tracking commitment. Decide if/when.
4. **Green-claims exposure.** Epic I's claims features carry live legal risk (EU EmpCo in force 27 Sep 2026; Green Claims Directive uncertain). The research says build carefully and last — recommend deferring.
5. **Standards-currency ownership.** Obligation rules (Epic C), SBTi V2.0 (Epic D), and disclosure formats (Epic G) all drift. This is ongoing maintenance, not one-time build — staff for it.

---

## 6. One-line summary

**Keep the product-PCF + supplier-data moat as the wedge; build the corporate 15-category inventory and the inbound request→answer loop on top of the engines that already exist (classifier, spend calc, versioning, primary-data loop, Cat-1 rollup); then layer targets, disclosure, and category depth — reversing the "no corporate inventory / no compliance report" posture only as a deliberate, staged expansion.**
