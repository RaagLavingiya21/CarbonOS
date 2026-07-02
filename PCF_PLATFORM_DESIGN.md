# PCF Platform Design — From BOM Calculator to Footprint Management Platform

**Status:** Approved design, pre-implementation
**Date:** 2026-07-02
**Informed by:** "Architecting Enterprise Systems for Product Carbon Footprint Management" (research report covering ISO 14067, GHG Protocol Product Standard, WBCSD PACT v3, Catena-X PCF Rulebook) and a full capability inventory of the current codebase.

---

## 1. Vision & Positioning

**The platform is the system of record where a sustainability analyst manages their organization's product carbon footprints — with AI workflows accelerating every step.**

Today the product is a set of AI workflows (BOM analyzer, supplier copilot, gap analyzer, advisor chat) wrapped around a single job: calculate a footprint from one BOM, once. Enterprise PCF platforms do more: they maintain a portfolio of product footprints with lifecycle and versions, track data quality as it improves, model reduction scenarios, and exchange footprints with customers and suppliers in standardized formats. This redesign repositions the product around those jobs. The AI workflows stay — but as accelerators inside each job, not as the product itself.

**What it is:** a screening-grade, spend-based PCF management platform aligned to the GHG Protocol Product Standard and the PACT v3 data exchange spec, with full traceability from every aggregate number down to its source citation.

**What it is not (non-goals):**
- Not a certification-grade LCA tool (no ISO 14067 conformance claim, no EPDs) — it does not replace an LCA practitioner's judgment
- Not a regulatory/compliance report generator
- Not an activity-based (process-LCI) calculator — the engine is spend-based (Open CEDA 2025, kg CO₂e per USD), and the product says so honestly everywhere results appear
- Not a decarbonization plan generator — it surfaces hotspots and models scenarios; the analyst decides

---

## 2. Personas

| Persona | Role in the platform | Today's coverage |
|---|---|---|
| **Sustainability analyst** (primary) | Creates and manages footprints, reviews flagged data, engages suppliers, models scenarios, publishes footprints. Business/data background, non-technical. Needs auditability above all. | Served by all existing modules |
| **Supplier** (secondary, external) | Receives data requests, provides primary emission data. Interacts via the engagement loop (email today; portal later). | Email drafting + response routing exist, but their data never reaches the footprint |
| **Downstream customer / auditor** (tertiary, external) | Requests and consumes published footprints; needs standardized, traceable payloads (PACT v3). | Not served at all today |

---

## 3. Core Jobs to Be Done

The five jobs an analyst must complete to manage product carbon footprints. Each maps to a stage of the enterprise PCF workflow identified in the research.

### Job 1 — Establish
> *"When a product needs a footprint, I want to turn its messy BOM into a credible, standards-aligned PCF, so I have a defensible baseline."*

| | |
|---|---|
| **Today** | Partial. CSV upload → parse/flag → CEDA factor match with confidence → calculate → critic validation → human checkpoints. Solid pipeline. |
| **Missing** | Footprint metadata that makes it a *PCF* rather than a number: declared unit, system boundary, reporting period, geography, product description. |
| **AI accelerator** | Fuzzy EF matching with confidence scores + flag-for-review (exists); chat-launched analyzer with intake form (exists). |

### Job 2 — Manage the portfolio
> *"When my organization has many products, I want to see every footprint's status, version, and quality in one place, so nothing is stale or unaccounted for."*

| | |
|---|---|
| **Today** | Weak. A flat "saved analyses" list; no statuses beyond approved/flagged, no versions, no portfolio view. |
| **Missing** | Products as first-class entities; footprint lifecycle (draft → calculated → under review → approved → published); versioning; recalculation; org-level dashboard with drill-down. |
| **AI accelerator** | Chat portfolio queries ("which products are still in draft?", "biggest footprint this quarter?"). |

### Job 3 — Improve data quality
> *"When my footprint is built on industry averages, I want to replace them with supplier-specific data, so the footprint reflects my actual supply chain — and I can prove it."*

| | |
|---|---|
| **Today** | Open loop. Supplier copilot ranks hotspot suppliers, drafts GHG-grounded emails, routes responses — but a supplier's data never updates the footprint. |
| **Missing** | Primary data records attached to line items; primary/secondary provenance; **Primary Data Share (PDS)** — the metric PACT and Catena-X make mandatory; recalculation on new data. |
| **AI accelerator** | Email drafting + response classification/routing (exists); "what would raise PDS most?" ranking (new, reuses engagement-candidate logic). |

### Job 4 — Reduce
> *"When I know my hotspots, I want to model material and supplier alternatives, so I can quantify reduction options before committing to them."*

| | |
|---|---|
| **Today** | Hotspot ranking only. |
| **Missing** | Scenario modeling: duplicate a baseline, swap a material/supplier/spend, compare side-by-side. |
| **AI accelerator** | Chat-driven scenario creation ("model Product X with recycled aluminum"). |

### Job 5 — Share
> *"When a customer requests my product's PCF, I want to publish a standardized, verifiable payload, so my footprint is usable across company boundaries."*

| | |
|---|---|
| **Today** | Nothing beyond CSV export. |
| **Missing** | PACT v3 `ProductFootprint` payload generation; publish semantics (immutable, versioned); read-only exchange endpoints. |
| **AI accelerator** | None needed — this job is deterministic serialization + validation, by design (auditors distrust generated numbers). |

---

## 4. User Journey

The analyst's end-to-end journey, with existing modules plugged into their proper places:

```
ONBOARD          ESTABLISH           MANAGE              IMPROVE             REDUCE              SHARE
────────         ─────────           ──────              ───────             ──────              ─────
Create org   →   Upload BOM      →   Portfolio view  →   Engage hotspot  →   Model scenario  →   Approve &
Invite team      (Analyzer)          statuses,           suppliers           swap material,      publish
                 Review flags        versions, PDS       (Copilot)           compare deltas      Export PACT
Run gap          Match factors       Drill into any      Supplier data                           payload
analysis to      Calculate           number down to      flows INTO the                          Respond to
scope Scope 3    Approve             its citation        footprint → PDS ↑                       PCF requests
(Gap Analyzer)   baseline
                                     ────────────────────────────────────────────────────
                                     Chat copilot spans the whole journey: query, launch,
                                     and drive any module from conversation (exists today)
```

Where the journey breaks today: everything right of ESTABLISH. The analyst calculates a footprint and then… starts over with the next CSV. There is no portfolio to manage, supplier responses dead-end in an engagements table, no scenarios, no publishable output. Phases 1–4 below repair the journey left-to-right in the user's chosen priority order (foundation first).

---

## 5. Information Architecture

Navigation shifts from **module-first** (Analyzer / Gap Analyzer / Copilot / Advisor as siloed tools) to **entity-first** (the things an analyst manages), with modules becoming actions on entities:

```
Dashboard                    org KPIs, every number drills down
└── Products                 the portfolio (list, filter, search)
    └── Product detail       footprint versions · line items · data quality ·
        │                    engagements · scenarios · audit trail
        ├── [Analyze]        → BOM analyzer (new version)
        ├── [Engage]         → supplier copilot (from a hotspot line item)
        ├── [Model]          → scenario builder
        └── [Publish]        → PACT payload export
Suppliers & Engagements      cross-product engagement tracking
Exchange                     published footprints + read-only PACT endpoints
Chat                         cross-cutting copilot; can launch/drive all of the above
```

The chat-first design stays — it's a differentiator — but chat becomes a way to *drive the platform*, not the only coherent surface.

---

## 6. Dashboard & Drill-Down Design

Design principle (and existing eval invariant): **every number in the output must have a traceable source.** The dashboard is built as three levels of traceability — every aggregate is a link to the records that produced it:

| Level | Surface | Example | Click-through |
|---|---|---|---|
| **L1 — Org KPIs** | Dashboard cards | Portfolio total: 14,200 kg CO₂e · Avg PDS: 12% · 3 products in draft · 7 open flags | → filtered product list |
| **L2 — Portfolio** | Products table | Trail Runner Shoe · v3 · Approved · 4,890 kg CO₂e · PDS 22% · 2 flags | → product footprint detail |
| **L3 — Footprint** | Line-item table | "Midsole foam · EVA · $1,240 spend · 610 kg CO₂e · 12.5% share · secondary · confidence 84" | → EF source citation ("Open CEDA 2025, Plastics, USA") or primary data record (supplier evidence) |

KPI cards worth having at L1: portfolio total kg CO₂e, products by lifecycle status, average PDS (with trend once Phase 3 lands), open flags awaiting human review, stale footprints (reporting period expired). Nothing on the dashboard is a dead-end number.

---

## 7. Target Data Model — PACT-Aligned `ProductFootprint`

Schema-first decision: the internal footprint record adopts the field structure of the PACT v3 `ProductFootprint` object, so export is serialization rather than translation, and later phases (PDS, versioning) land on standards-shaped ground.

| PACT v3 field | Our column | Notes |
|---|---|---|
| `id` | `footprint_uuid` | RFC 4122 UUID per footprint version |
| `specVersion` | `spec_version` | "3.0.0" |
| `productIds` | derived: `urn:pfa:product:{product_id}` | internal SKU URN |
| `companyName` / `companyIds` | from `organizations` | org name; URN from org id |
| `productDescription` | `product_description` | new intake field |
| `created` / `updated` | `created_at` / `updated_at` | exists |
| `pcf.declaredUnit` | `declared_unit` | default **"piece"** — see below |
| `pcf.unitaryProductAmount` | `unitary_product_amount` | default 1 |
| `pcf.fossilGhgEmissions` | `total_kg_co2e` | exists; serialized as decimal string per spec |
| `pcf.reportingPeriodStart/End` | `reporting_period_start/end` | new intake fields |
| `pcf.geographyCountry` etc. | `geography_country` (nullable) | enforce PACT mutual-exclusivity rules (global ⊕ region ⊕ country ⊕ subdivision) |
| `pcf.primaryDataShare` | `primary_data_share` | computed; **0% until Phase 3** |
| `pcf.dqi` | `dqi` (JSONB) | placeholder scores initially; honest "secondary EEIO" grading |
| `pcf.boundaryProcessesDescription` | `system_boundary` | locked "cradle-to-gate" |
| — | `status` | lifecycle: draft → calculated → under_review → approved → published |
| — | `version` | integer; recalculation creates version n+1; published versions immutable |

`line_items` gains `data_source` (`secondary` default / `primary`) — the atom from which PDS is computed: **PDS = Σ kg CO₂e from primary-sourced line items ÷ total kg CO₂e**.

**Spend-based mapping, stated honestly:** the engine is spend-based (kg CO₂e per USD, Open CEDA 2025), so the declared unit is "1 piece of the assessed product" and the PCF is total cradle-to-gate kg CO₂e per piece. Methodology metadata in the payload records the spend-based EEIO approach and per-line-item source citations. PDS starting at 0% is not a bug — it's the honest baseline that Job 3 exists to improve, and the metric PACT requires us to disclose.

---

## 8. Roadmap

Priority order chosen: foundation first (schema), then the surfaces on top of it, then the loops that make the numbers move.

### Phase 1 — PACT-aligned data foundation + export *(Job 5: Share)*
- Migrate `products` → footprint-shaped record (columns in §7); `line_items` + `data_source`
- Analyzer intake collects product description, reporting period, geography
- `GET /api/footprints/{id}/pact` — serialize to PACT v3 JSON (decimals as strings, mandatory-field + geography validation); stretch: read-only `GET /footprints` list endpoint (the "exchange API" story)
- Frontend: "Export PACT payload" with preview on the saved analysis view
- **Success:** payload validates against the official PACT v3 JSON schema (wbcsd/data-exchange-protocol)
- **Demo:** upload BOM → approve → export PACT payload → validate against schema

### Phase 2 — Portfolio & footprint lifecycle *(Job 2: Manage)*
- Lifecycle statuses + versioning (immutable once published; recalculation → v n+1); surface existing `audit_log`
- `/products` portfolio page; `/products/{id}` detail page (versions, line items with citations, hotspots, linked engagements)
- Dashboard rework: L1→L2→L3 drill-down per §6
- Chat `analysis` skill: portfolio queries
- **Demo:** dashboard KPI → click through three levels → land on an EF citation

### Phase 3 — Primary data loop + PDS *(Job 3: Improve — closes the copilot loop)*
- Copilot `STORE_DATA` routing writes a primary data record to the line item; line item recalculates; `data_source` → primary; provenance retained (original CEDA factor + supplier evidence)
- PDS computed and live in the PACT payload; recomputation → new footprint version
- UI: primary/secondary badges, PDS on portfolio + dashboard, engagement detail shows "raised Product X's PDS from a% → b%"
- Chat skill: "what would raise PDS of Product X most?"
- **Demo:** route a supplier response → watch the footprint version bump and PDS rise

### Phase 4 — Scenario modeling *(Job 4: Reduce)*
- "Duplicate as scenario" on any version: editable copy (swap material → re-run EF match; edit spend), never publishable
- Side-by-side compare: total + per-line-item deltas vs baseline
- Chat skill: "model Product X with recycled aluminum"
- **Demo:** duplicate baseline → swap a hotspot material → compare deltas

**Cross-cutting every phase:** new eval invariants ("PACT payload mandatory fields always present", "PDS = primary kg CO₂e ÷ total kg CO₂e", "published versions never mutate"); business logic stays out of `api/routes/` and the UI per existing dependency rules.

### Explicitly deferred (future section, not built now)
- Activity-based / hybrid calculation engine (decision: spend-based only)
- Multi-tier BOM graph, co-product allocation, biogenic emissions split
- PACT `POST /events` async exchange, OAuth host API, PACT Conformance Tool certification

---

## 9. What Already Exists to Build On

| Existing asset | Role in the redesign |
|---|---|
| `parsing/bom_parser.py`, `factors/ef_lookup.py`, `calc/footprint.py`, `calc/critic.py` | Untouched core pipeline — Job 1 engine |
| `products` / `line_items` tables + analyses endpoints (19 migrations, RLS) | Extended into the footprint model, not replaced |
| `copilot/exception_router.py` `STORE_DATA` path | The exact hook where Phase 3 closes the loop |
| Chat agent skills registry (`api/agent/`) | Each phase ships as added skill capabilities |
| Frontend `/analyzer` save flow, `PanelContext`, API client | Intake fields and export button slot in here |
| `audit_log` table | Surfaced in Phase 2 for the auditability story |
