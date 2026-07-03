# Product Strategy & Gap Assessment

*Where the Product Carbon Footprint platform sits against what enterprise PCF users actually need — and what to build next. A product-management assessment, not a technical spec.*

## Method

This assessment anchors on the enterprise PCF workflow described in our research (the 6-stage flow: BOM ingestion → activity-data collection & gap-filling → emission-factor mapping → calculation/hotspots → data quality & scenario modeling → PACT data exchange) and its four named differentiators (AI-assisted EF mapping, a hybrid calculation engine, dynamic scenario modeling, and regulatory/framework translation). Each of the five core jobs — **Establish, Manage, Improve, Reduce, Share** — is graded by *real analyst pain*, not feature count.

## Where the product sits today

| Core job | What the user actually needs | What we built | Maturity |
|---|---|---|---|
| **Establish** | Ingest product structures at scale (ERP/PLM sync, multi-tier BOM); AI-map messy descriptions to factors with confidence + human override | Single-CSV upload, parse/flag, spend-based CEDA match with confidence + citations + suggestions, human checkpoints | **Functional, not at scale** |
| **Manage** | Portfolio of many SKUs; lifecycle; versioning; recalculation triggers when inputs drift >10%; review/approval | Portfolio, draft→approved→published lifecycle, versioning/lineage, immutability, dashboard drill-down | **Functional** |
| **Improve** | Primary-data maximization; PDS **and DQR** (data-quality rating); supplier data collection | Primary-data loop (supplier + manual) → PDS rises; supplier copilot (rank/draft/route) | **Functional — strongest new work** |
| **Reduce** | Duplicate a baseline; swap material/grid/recycled content; see projected reduction instantly | Scenario modeling: material + spend swap, side-by-side compare, per-line deltas | **Functional** |
| **Share** | Participate in the exchange network — serve footprints to downstream customers, request from upstream suppliers (PACT REST + events); roll up to corporate Scope 3 | Export a schema-valid PACT v3 JSON file per footprint | **Prototype — a file, not participation** |

**Honest one-line read:** we built an auditable, standards-aligned **screening** platform where an analyst can establish, manage, improve, reduce, and *export* a product footprint end-to-end. Two things most undercut the product's own promise: the "auditable" claim leans on a **data-quality rating that is currently stubbed**, and "Share" is a **file, not the network** the research says the value lives in.

## Gap analysis — where a human analyst still gets stuck

- **Establish** — Gets one product in at a time (no bulk/templated import, no ERP sync). The factor library is thin, so many matches land low-confidence and must be eyeballed, and the analyst can *flag* a bad EF match but can't easily **override, correct, or teach** it. At a 500–5,000-person company with dozens of SKUs, the front door is the bottleneck.
- **Manage** — No **maker-checker**: one person calculates *and* approves, which no audited enterprise accepts. No **staleness/drift signal**, so an analyst holding 50 footprints can't tell which are outdated or have crossed the 10% recalculation threshold the standards flag.
- **Improve** — **DQR is hardcoded (4/4/4)** in the PACT export, so the single most important "how good is this number?" signal is fake. Supplier engagement is **email-simulated**, with no real inbound data channel (portal or PACT events). No **PDS trend** over time.
- **Reduce** — Levers are limited to material and spend (no grid-mix, transport, or recycled-content presets). No **target-setting or progress tracking**. No portfolio-level "where is my biggest reduction opportunity across all products?"
- **Share** — The tertiary persona we defined (**downstream customer / auditor**) can receive nothing but a file the analyst emails. There is no way to **respond to a customer's PCF request**, and no **roll-up** to the corporate Scope 3 Category 1 number — which is *why the company funds this work at all*.

## The strategic frontier — three big bets, named deliberately

**1. Hybrid activity-based engine.** Calculate via process LCI (ecoinvent-style) where physical quantities exist, and fall back to spend-based CEDA otherwise. Unlocks decision-grade (not just screening) numbers and a higher PDS ceiling. Cost: licensed data, a much larger data model, and activity quantities the BOM often lacks. **Call: defer, but design toward it.** This is the line between "screening tool" and "the analyst's real engine," but the screening positioning is honest and defensible today; forcing the engine early buys cost and complexity before the rest of the journey is solid.

**2. Live PACT exchange network.** Implement the PACT REST API as *host* (serve footprints, answer PCF-request events) and *client* (request upstream data). Unlocks the actual Share job, serves the tertiary persona, and automates supplier collection — replacing email. Cost: OAuth2, data sovereignty, RBAC, conformance. **Call: highest-leverage bet — build a thin slice.** A shareable footprint plus an inbound request inbox proves the vision without full network conformance.

**3. Corporate Scope 3 roll-up.** Aggregate approved footprints × volumes into the Scope 3 Category 1 number, mapped to GHG Protocol / CSRD categories. Unlocks the connection to corporate ESG disclosure and serves the sustainability lead above the analyst. Cost: needs production/sales volumes; brushes the "no regulatory filing" non-goal (a *view* is not a *filing*). **Call: high-value fast-follow** — it reframes the product from "product footprints" to "the product-level foundation of your corporate carbon report."

## Prioritized roadmap

*Prioritization logic: fix where the product most under-delivers on its **own** promise first — auditability and Share — before adding new surface area.*

**Wave 1 — Make the trust real** (deepen the current positioning). The core promise is "auditable / standards-grade"; close the gaps that make that partly untrue today.
- Real **DQR scoring** (technological / temporal / geographical representativeness) → an honest PACT export plus a per-footprint data-quality surface.
- **Footprint confidence + provenance view** — consolidate citations and version history into an auditor-facing "how every number was derived" statement.
- **Portfolio health** — staleness/drift flags; which footprints need recalculation.
- **Maker-checker** — restore `under_review` and second-person approval.

**Wave 2 — Close the Share loop** (the network, thin slice). Share is the least-mature job and the research's central thesis.
- **Serve** — an access-controlled, shareable footprint a downstream customer or auditor can pull.
- **Receive** — an inbound "PCF request" inbox: a customer asks for a product's footprint, the analyst fulfils it from the portfolio (mirrors PACT events without full conformance).

**Wave 3 — Connect to *why*** (corporate roll-up). Aggregate to the Scope 3 Category 1 / ESG view; elevate from analyst tool to the foundation of corporate disclosure.

**Designed-for, not built — the hybrid activity engine.** The v2 move from screening-grade to decision-grade.

## What we deliberately will *not* build (and why)

- **Full regulatory report generation** — stay a data/intelligence layer, not a filing tool (standing non-goal).
- **Certification-grade LCA / EPD conformance** — defer to LCA practitioners (standing non-goal).
- **Multi-tier BOM graph** — over-engineering while the engine is spend-based; revisit only if the activity engine lands.
- **Becoming a factor-database vendor** — integrate ecoinvent/DEFRA, don't rebuild them.

## Strategic narrative

Today the product is an auditable, standards-aligned screening platform covering all five jobs end-to-end for the individual analyst. The next arc makes the trust *real* (DQR + provenance), turns Share from a file into *participation* in the PACT network, and connects product footprints to the corporate carbon number that justifies the whole exercise — a deliberate path from "a good analyst tool" to "the system of record that sits between an organization's supply chain and its climate disclosure," while consciously staying out of certification-grade LCA and regulatory filing.
