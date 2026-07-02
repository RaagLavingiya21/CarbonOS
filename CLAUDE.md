# CLAUDE.md — Product Carbon Footprint Analyzer

## Project Purpose
This project is to create a tool which will be used by sustainability analysts at consumer goods companies to estimate product-level Scope 3 footprints from messy BOM data so they can identify hotspots and prioritize supplier engagement. The tool fetches and parses the material data from uploaded bill of materials, fixes or flags messy or incomplete bill of material data, fetches emission factor from external emission factors database, calculates products emission footprint based on the BOM and emission factors. This enables the user to understand product's total emission, emission hotspots, and design decarbonization strategies to reduce the carbon footprint of product. 

## Product Direction (source of truth)

**`PCF_PLATFORM_DESIGN.md` is the product source of truth.** Read it before implementing any feature. The product is being repositioned from "a BOM calculator with AI features" to "the platform where a sustainability analyst manages their organization's product carbon footprints," anchored on five core jobs: **Establish, Manage the portfolio, Improve data quality, Reduce, Share.**

Key standing decisions (do not re-litigate in implementation sessions):
- The calculation engine stays **spend-based** (Open CEDA 2025, kg CO₂e per USD). No activity-based/hybrid engine. Results are labeled screening-grade.
- The internal footprint data model mirrors the **WBCSD PACT v3 `ProductFootprint`** schema (declared unit, reporting period, geography, primary data share, status, version), so export is serialization, not translation.
- Footprints have a lifecycle: `draft → calculated → under_review → approved → published`. Published versions are immutable; recalculation creates version n+1.
- Build order: ① PACT data foundation + export → ② portfolio & lifecycle → ③ primary data loop + PDS → ④ scenario modeling.
- Every aggregate number in the UI must drill down to the records that produced it (KPI → product → line item → source citation).


## User Persona
This tool will be used by a sustainability analyst or business analyst. The company size - 500 to5,000 employees. 
- Users will have some business and data analysis, sustainability, financial, legal, and accounting background, but won't have a technical and coding knowledge. 
- Users require the tool results to be auditable, the methodology to be standard and reliable
- The user will use the outcome of the tool to Understand the total emission of the product, and the breakdown of emission from product components and drive decision making around:
- where the emission hotspots are
- which components are the most emitting
- how they can reduce the emission from the overall product as well as from components
- how they can choose different suppliers or different materials or different quantities or different methods to generate the same product in a lower-carbon-emission way

## Domain Context

- **BOM**: Bill of Materials(BOM) is a list of all the components, the material used in components, the quantity and weights of the material. It's the recipe of product with all the ingridients
- **Emission factor**: Emission factor is an estimate of greenhouse gases released from a specific activity. It can be measured in different units, like ton of CO2 per kg of a material or ton of CO2 per kWh of electricity. 
- **Activity data**: a quantitative measure of a company’s operational activities that generate greenhouse gas emissions, such as fuel consumption, energy use, or materials purchased

- **GWP**: It is global warming potential. It is a measure of the warming effect a gas has over a certain time period. Generally GWP100(warming potenital over 100 year time period) is used and is normalized in CO2e(CO2 equivalence). 

- **Cradle-to-gate**: It is one of the boundary condition for life cycle analysis (LCA). It means from raw material extraction through manufacturing, up to the point the product leaves the factory gate. It is different from Cradle to Grave, which also includes use of the product and end of life, and Gate to Gate, which only includes manufacturing. 

- **Scope 3 Category 1**: is Purchased Goods and Services — emissions from the production of goods and services a company buys.

- **Primary vs Secondary data**: Primary data is firsthand, supplier-specific, or facility-level data (e.g., energy bills, direct emissions) from a company’s value chain. Secondary data is industry-average data (e.g., databases, literature) used when primary data is unavailable

- **Hotspot** : A hotspot is a material, process, or supplier that contributes a disproportionately large share of a product's footprint, making it a priority for reduction efforts.
(and so on)

## Architecture

Four modules, strict dependency direction:

- `parsing/` — BOM ingestion, normalization, unit standardization
- `factors/` — emission factor lookup from external databases (ecoinvent, USEEIO)
- `calc/` — emission calculations, aggregation, hotspot identification
- `app.py` — Streamlit UI, user interaction, result display

**Dependency rules:**
- `app.py` imports from `calc/`, `factors/`, `parsing/`. Nothing imports from `app.py`.
- `calc/` imports from `factors/` and `parsing/`. 
- `factors/` imports from `parsing/`. 
- `parsing/` imports from nothing internal.

**Hard constraints:**
- No Streamlit calls outside `app.py`
- No calculations inside `app.py`, `factors/`, or `parsing/`
- No emission factor lookups inside `app.py` or `calc/`
- `calc/`, `factors/`, and `parsing/` must be runnable from a plain Python script with no UI dependency


## Decision Rules for Ambiguous Inputs
Bullet list. One bullet per case:
- Missing spend_usd → flag for human review
- Missing component or material → flag for human review
- Formatting discrepancy → fix it
- Ambiguous material → suggest nearest matches,flag for review
- A unit is in imperial (lb, oz) instead of metric - convert to metric
- Two rows look like duplicates → proceed but flag
- Supplier data contradicts previous submission → flag with explanation
- Low-confidence emission factor match → proceed but flag with confidence score
 

## Non-Goals
- It does not prepare a regulatory or compliance report. 
- It does not produce a decarbonization plan.  
- This tool does not replace an LCA practitioner's judgment for certification-grade assessments (e.g., EPDs, ISO 14067 conformance).


## Eval Invariants
- Total footprint must equal the sum of the individual footprint of all the material line items. 
- total kg of co2e = spend_usd x emission factor
- Every emission factor must have a source citation
- Every number in the output must have a traceable source. 
- every emission factor's activity unit must match the activity unit in the BOM row it's applied to.
- Unit mismatches must be resolved by conversion
- Same input must produce the same output in terms of total footprint. 
- Unmatched items must must be flagged for human review. 
- Confidence below threshold must must be flagged to human as low confidence. 
- Every exported PACT payload must contain all PACT v3 mandatory fields and pass the official PACT v3 JSON schema; decimals serialized as strings; geography fields mutually exclusive.
- Primary Data Share (PDS) = kg CO₂e from primary-sourced line items ÷ total kg CO₂e. A footprint with no supplier-provided data has PDS = 0%.
- A published footprint version must never change; any recalculation produces a new version.


## Architecture (Production Target)

The app is being upgraded from a Streamlit prototype to a production stack:
- **Backend:** FastAPI (Python, async) in `api/` — all business logic exposed as REST endpoints
- **Frontend:** Next.js 14 + TypeScript + shadcn/ui in `frontend/` — deployed on Vercel
- **Database:** Supabase (Postgres) with Row-Level Security — replaces SQLite
- **Agent orchestration:** LangGraph StateGraphs in `api/graphs/` — replaces manual planner-executor
- **Observability:** LangSmith for tracing + evals (auto-traces LangGraph runs)
- **Auth:** Supabase Auth (JWT verified in FastAPI middleware)

The original Streamlit app (app.py, pages/) is kept during migration but is not the target frontend.

See `Architecture_Decisions.md` for detailed rationale behind each choice.
See `IMPLEMENTATION_PLAN.md` for the phased build sequence (stack migration).
See `PCF_PLATFORM_DESIGN.md` for the product design and the current 4-phase feature roadmap.

**Dependency rules (unchanged):**
- `calc/`, `factors/`, `parsing/`, `llm/`, `rag/`, `gap_analyzer/`, `copilot/`, `db/` are business logic — no UI imports
- `api/routes/` imports from business logic modules
- `frontend/` communicates with backend only via HTTP (FastAPI endpoints or Supabase client)
- No Streamlit calls outside `app.py` and `pages/`

## Coding Conventions
- Python 3.13 for backend. Ruff formatter.
- TypeScript strict mode for frontend. ESLint + Prettier.
- All units should encode what they represent — e.g. `total_kg_CO2e` rather than just `total`
- Pytest for Python tests. Vitest for frontend tests.
- FastAPI endpoints use Pydantic models for request/response validation
- Async functions for all I/O-bound operations (LLM calls, DB queries)

## Rules for AI-Assisted Implementation
Development is split: implementation plans are authored per phase (by Claude), then executed by an AI implementer (Cursor or Claude). When implementing:
- **Follow the phase's implementation plan exactly.** Do not refactor, rename, or "improve" code outside the plan's stated scope. If the plan seems wrong or incomplete, stop and say so rather than improvising.
- **Never write credentials, API keys, or Supabase URLs into source files.** Configuration comes from environment variables only (`.env` is gitignored). Never commit `.env` files.
- **Test database migrations against a local/branch database first** — never run an untested migration against the database holding demo data.
- CI must pass before a PR is mergeable: ruff + pytest + golden-file evals (backend), ESLint + `next build` (frontend).
- New logic that implements an Eval Invariant ships with a pytest that enforces it.

## When to Ask the User
Missing quantity → flag for human review
- Missing component or material → flag for human review
- Anomolus quanity → flag for human review
- Ambiguous material → suggest nearest matches,
  flag for review
- No direct match for emission factors in EEIO or EcoInvent database -> suggest nearest matches, flag for review



