# Implementation Plan — Epic I: Levers, MAC, Decisions & Green-Claims

**Branch:** `feature/scope3-mvp`
**Status:** Plan, pre-implementation
**Source:** `03-enhancement-roadmap.md` Epic I; `00-program-overview.md` §2. Depends on **Epic A** (inventory) and **Epic H** (activity/use-phase data for lever modeling). Reuses the product **scenario engine** and supplier ranking. **Claims features are legally gated — build last, carefully (§1).**

> **What this epic is.** The research's **JTBD-3 ("find what to do") + the decision/act layer.** A curated consumer-lever library with rough abatement/cost, corporate trajectory + MAC-curve modeling, decision support embedded in procurement and product workflows, and — carefully — green-claims substantiation with jurisdiction compliance flags. This is where measurement becomes action.

> **What this epic is NOT.** Not a decarbonization-plan *generator* — it surfaces and quantifies options; the analyst decides (an explicit CarbonOS non-goal that stays). Not target-setting (Epic D). Not a legal opinion on claims (§1).

Research units closed: **P.3.5.a** (consumer lever library), **P.3.5.b** (scenario/trajectory modeling), **P.3.5.c** (MAC curve), **P.4.5.a** (green-claim substantiation), **P.4.5.b** (compliance/risk flagging), **P.4.6.a** (procurement decision support), **P.4.6.b** (product/portfolio decision support).

---

## 1. The green-claims legal constraint (read first — governs the claims sub-epic)

Claims are the one place in the program with **direct legal exposure**, and the research says build them carefully and last. Enforced as design rules + invariants:

1. **Substantiation is conservative and evidence-bound.** A claim is only substantiable from **primary-data-backed, method-labeled figures** (Epic A PDS + Epic G assurance lineage). Spend-based screening estimates **cannot** substantiate a public claim — the tool refuses and says why. No LLM-generated claim language presented as substantiated.
2. **Jurisdiction compliance flags are first-class.** Per `research/reg-status-verified.md`: **EU EmpCo (Directive 2024/825) in force 27 Sep 2026** bans offset-based B2C "carbon neutral/positive" claims outside the value chain; **EU Green Claims Directive is SUSPENDED** (build to EmpCo, not GCD — flag as watch); **US FTC Green Guides = 2012 version still operative**. The compliance flagger encodes these dated rules (versioned data, like the obligation ruleset) and **flags offset-based neutrality claims as prohibited in the EU B2C context**.
3. **Claims ship last.** I1–I3 (levers, MAC, decisions) have no legal exposure and can ship first; I4 (claims) ships only after review and can be deferred entirely without blocking the rest of the epic.

Shared discipline (non-claims parts): abatement/cost figures are estimates clearly labeled as rough; scenario numbers come from the scenario engine, not the LLM.

---

## 2. Structure

```
I1 levers ──► I2 MAC / trajectory ──► I3 decisions (procurement + product)      [no legal exposure — ship first]
     └────────────────────────────────► I4 claims substantiation + compliance flags   [legal-gated — ship last / optional]
```

---

## 3. New data model (migrations `053`–`054`)

| Table | Purpose | Key columns |
|---|---|---|
| `levers` | Curated consumer decarbonization levers | `lever_id`, `category_num`, `name`, `abatement_estimate`, `cost_estimate`, `applicability`, `source` |
| `claims` | A substantiation attempt + compliance verdict | `claim_id`, `org_id`, `product_id`, `claim_text`, `substantiated` (bool), `evidence_ref`, `jurisdiction`, `compliance_status`, `ruleset_version` |

Reduction scenarios reuse the existing `scenarios` table (023) extended to corporate trajectories.

---

## 4. New modules (business logic — no UI imports)

| Module | Responsibility | Reuses |
|---|---|---|
| `levers/library.py` | Curated lever library + applicability matching (P.3.5.a) | curated content; category tags |
| `levers/mac.py` | Trajectory + MAC-curve modeling (P.3.5.b/.c) | **scenario engine** (`scenario_store.py`); Epic D trajectory |
| `decisions/procurement.py` | Procurement/supplier decision support (P.4.6.a) | supplier ranking; Cat 1/4 hotspots |
| `decisions/product.py` | Product/portfolio decision support (P.4.6.b) | product PCF; Epic H use-phase; scenario engine |
| `claims/substantiation.py` | Evidence-bound claim substantiation (P.4.5.a) — **gated §1.1** | Epic A PDS; Epic G lineage |
| `claims/compliance.py` | Jurisdiction compliance flags (P.4.5.b) — dated ruleset §1.2 | `data/claims_rules/{version}.yaml` |
| `db/lever_store.py`, `db/claims_store.py` | CRUD | `db/store.py` |

---

## 5. API routes (`api/routes/decisions.py` — orchestrate only)

| Endpoint | Method | Does |
|---|---|---|
| `/api/levers` | GET | Lever library filtered by category/applicability |
| `/api/mac` | POST | MAC curve / trajectory for chosen levers |
| `/api/decisions/procurement` | POST | Procurement decision support for a category |
| `/api/decisions/product` | POST | Product/portfolio decision support |
| `/api/claims/substantiate` | POST | Attempt substantiation (gated) + compliance flags |

---

## 6. Sub-phases

### I1 — Lever library  (P.3.5.a)
- **Goal:** Curated consumer levers with rough abatement/cost, matched to a company's hotspots.
- **Verify:** Levers filter by category; abatement/cost labeled as rough estimates with sources.
- **Prompt:** *Read §3. Create `levers/library.py` + `data/levers/*.yaml` (consumer levers: low-carbon materials, packaging redesign, modal shift, regenerative ag, etc.) with abatement/cost estimates + sources. Match to Epic A hotspots. Wire `GET /api/levers`.*

### I2 — MAC / trajectory modeling  (P.3.5.b/.c)
- **Goal:** Model a decarbonization trajectory and rank levers by $/tCO2e.
- **Verify:** Trajectory reuses the scenario engine; MAC ranks levers by cost-effectiveness; numbers from the engine.
- **Prompt:** *Read §1 (labeling), §4. Create `levers/mac.py`: extend the product scenario engine to corporate trajectories; rank chosen levers by $/tCO2e into a MAC curve; tie to the Epic D target. Wire `POST /api/mac`.*

### I3 — Decision support  (P.4.6.a/.b)
- **Goal:** Embed carbon in procurement + product decisions.
- **Verify:** Procurement support ranks suppliers/materials by carbon for a category; product support compares SKU redesign options (incl. Epic H use-phase).
- **Prompt:** *Read §4. Create `decisions/procurement.py` (rank sourcing options by carbon, reuse supplier ranking + Cat 1/4 hotspots) and `decisions/product.py` (SKU/portfolio comparison reusing product PCF + Epic H + scenario engine). Wire the two decision routes.*

### I4 — Claims substantiation + compliance flags  (P.4.5.a/.b) — LEGAL-GATED, ship last
- **Goal:** Evidence-bound substantiation + jurisdiction compliance flagging.
- **Verify:** A claim substantiates only from primary-data-backed figures (Epic A PDS + Epic G lineage); a spend-based estimate is refused with explanation. An offset-based B2C "carbon neutral" claim is flagged **prohibited in EU** (EmpCo). Ruleset versioned; GCD marked suspended/watch.
- **Prompt:** *Read §1 in full. Create `claims/substantiation.py` (substantiate ONLY from primary-data-backed, method-labeled figures — refuse spend-based screening estimates with a reason) and `claims/compliance.py` + `data/claims_rules/v2026-07.yaml` (EmpCo 27 Sep 2026 offset-B2C ban = prohibited; GCD suspended = watch; FTC 2012). Wire `POST /api/claims/substantiate`. Do not ship without review.*

### I5 — Evals
- **Prompt:** *Write `tests/test_decisions.py` and `tests/test_claims.py` for §7 — especially the substantiation-refusal and EmpCo-prohibition invariants.*

---

## 7. New eval invariants

- Lever abatement/cost values are labeled rough estimates and carry a source.
- MAC/trajectory numbers come from the scenario engine; none LLM-generated.
- A claim substantiates only from primary-data-backed, method-labeled figures; a spend-based-only estimate is refused with a stated reason.
- An offset-based B2C neutrality claim is flagged prohibited in the EU (EmpCo); the claims ruleset is dated + versioned; GCD is marked suspended (watch).
- Decision-support rankings trace to inventory/hotspot/PCF data.

---

## 8. Risks & decisions

| Item | Type | Handling |
|---|---|---|
| **Green-claims legal exposure** | 🔴 | §1: conservative, evidence-bound, jurisdiction-flagged; ship I4 last, after legal review; deferrable without blocking I1–I3. |
| GCD status uncertain | 🟠 | Build to EmpCo not GCD; mark GCD suspended/watch (research). |
| Abatement/cost estimate quality | 🟠 | Label everything rough; not an optimization engine (research: shortlist, not full MAC optimization, for this ICP). |
| Not a plan generator | 🟢 (non-goal kept) | Surfaces + quantifies options; analyst decides. |
| Depends on A + H | 🟠 | Lever/product modeling needs activity/use-phase data; sequence after H. |

---

## 9. Definition of done

An analyst sees a **shortlist of consumer-relevant levers** matched to their hotspots with rough abatement/cost, models a **trajectory + MAC curve** toward the Epic D target, and gets **procurement and product decision support** that embeds carbon in real sourcing/SKU choices. Where — and only where — a footprint is primary-data-backed and assured, they can attempt a **substantiated green claim**, with the tool **refusing weak claims and flagging EU-prohibited offset-neutrality claims** under EmpCo. Measurement has become defensible action, and the full A→I platform is specified end-to-end.
