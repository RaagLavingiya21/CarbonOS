# Implementation Plan — Epic C: Driver & Obligation Front Door

**Branch:** `feature/scope3-mvp`
**Status:** Plan, pre-implementation
**Source:** `03-enhancement-roadmap.md` Epic C. Runs parallel to Epics A/B as the top of the funnel; C4 (SBTi coverage math) depends on Epic A.

> **What this epic is.** The research's **JTBD-0: "tell me if this is my problem yet."** Given a company profile, diagnose *which drivers actually bite* (SB253/261 revenue thresholds, CSRD exposure, SBTi obligation, customer/retailer requests) and translate them into a ranked "why + what's due when" roadmap and a business case. This is what opens the budget — the analyst arrives here before they ever build an inventory.

> **What this epic is NOT.** Not the questionnaire response (that's Epic B). Not the SBTi *target wizard* (that's Epic D) — Epic C only does the *readiness/trigger* diagnosis (are you obligated, are you Category A/B, is your coverage sufficient). Not a legal opinion — it's a screening tool that flags exposure and cites the rule.

Research units closed: **P.1.1.b** (obligation rules engine), **P.1.1.c** (ranked obligation & timeline), **P.1.1.d** (business-case / why-now), **P.1.3.a/.b** (SBTi trigger/coverage readiness + commit→validation timeline), **P.1.4.a** (priority scoring), **P.1.4.b** (cascade-exposure detection). (P.1.1.a intake is extended here; P.1.2 request capture lives in Epic B.)

---

## 1. The currency constraint (read first — it governs the whole design)

Every driver this epic encodes is **moving**, and the research repeatedly warns the engine must stay current and must not overstate certainty. Two rules, enforced structurally:

1. **The ruleset is data, not code.** Obligation rules live in a **dated, versioned file** (`data/obligation_rules/{version}.yaml`), not in Python `if` statements. Each evaluation records which `ruleset_version` it used. Updating for a regulatory change = editing a reviewed data file, not a code change. This is the single most important design decision in the epic (the research flags P.1.1.b as 🟠 "must stay current — SB253, CSRD Omnibus, SBTi V2.0").
2. **Uncertainty is a first-class status.** Where the verified research says a rule is unconfirmed or in flux, the engine returns `status: uncertain/watch` **and says so** — it never asserts a fixed value. Specifically (per `research/reg-status-verified.md`): the **SBTi V2.0 net-zero coverage %** is not cleanly confirmed → *do not hardcode*; **SB253 Scope 3 report format** is open until CARB's final reg (~end-2026) → flag; **SB261** enforcement is under a Ninth-Circuit injunction → flag. The engine surfaces these as watch-items, not obligations-with-fixed-numbers.

---

## 2. The rules the engine must encode (from `research/reg-status-verified.md`, dated 2026-07-04)

Each becomes a dated rule with a predicate over the company profile, a due date, an assurance note, a citation, and a confidence/status. **These are the verified values to seed `v2026-07` of the ruleset** — treat as a snapshot, not eternal truth.

| Driver | Trigger predicate | What's due / when | Confidence |
|---|---|---|---|
| **CA SB 253** | US entity, **>$1B global revenue**, doing business in CA | Scope 1&2 report (CARB deadline ~10 Nov 2026); **Scope 3 from 2027**; assurance limited→reasonable | ⚠️ Scope 3 *format* open (final reg ~end-2026) |
| **CA SB 261** | US entity, **>$500M revenue**, doing business in CA | Biennial climate-risk report (TCFD/IFRS-S2-aligned) | ⚠️ under 9th-Cir injunction |
| **CSRD / ESRS E1** (post-Omnibus) | **>1,000 employees AND >€450M net turnover**; OR non-EU Art. 40a: **>€450M EU group turnover + qualifying EU subsidiary/branch >€200M** | Scope 1/2/3 + value-chain data, iXBRL; first reports FY2027→2028 | ✅ (Omnibus in force 18 Mar 2026) |
| **IFRS S2 / ISSB** | Foreign-listed parent, or supplier to a caught co. | Scope 3 per GHG Protocol; jurisdiction-phased | ✅ indirect for ICP |
| **US SEC climate rule** | — | **Discount** — effectively dead (rescission proposed 2026) | ✅ not a driver |
| **SBTi V2.0** | **Category A** = revenue >$1B OR >500 employees OR significant emissions (high-income) → **Scope 3 targets MANDATORY + base-year limited assurance** | Standard effective 31 Jan 2027; V2.0 mandatory after 31 Jan 2028; per-category ≥5% coverage | ✅ near-term rule; ⚠️ net-zero % unconfirmed |
| **Customer / retailer request** | Sells to Walmart / Tesco / CDP-SC / EcoVadis buyer | Contract-linked questionnaire — **routes to Epic B** | ✅ the real wedge |

**ICP shortcut the engine should surface:** a mid-market consumer brand is *revenue-large by default* (>$1B common) and >500 employees → **almost always SB253-exposed AND SBTi Category A** (Scope 3 targets mandatory + base-year assurance). That is the headline "why now" for this segment.

---

## 3. New data model (migrations `058`–`059`)

| Table | Purpose | Key columns |
|---|---|---|
| `company_profiles` | Persisted org profile driving the engine (extends the transient gap-analyzer `CompanyProfile`) | `org_id`, `annual_revenue_usd`, `eu_turnover_eur`, `eu_subsidiary` (bool), `employee_count`, `geographies`, `listed_status`, `sector`, `key_customers` (jsonb), `updated_at` |
| `obligations` | Evaluated obligations per org | `obligation_id`, `org_id`, `framework`, `applies` (`yes`/`no`/`uncertain`), `trigger_reason`, `threshold_detail`, `due_date`, `assurance_requirement`, `status`, `confidence`, `citation`, `ruleset_version`, `evaluated_at` |

The **ruleset itself is a versioned file**, not a table: `data/obligation_rules/v2026-07.yaml` (+ a loader). Rules in git = reviewable diffs when regs move.

---

## 4. New modules (business logic — no UI imports)

| Module | Responsibility | Reuses |
|---|---|---|
| `obligations/ruleset.py` | Load + validate the dated ruleset file; expose rules as predicates + metadata | — (new; schema-validated YAML) |
| `obligations/engine.py` | Evaluate a `company_profile` against the ruleset → ranked obligations + timeline; records `ruleset_version` | `obligations/ruleset.py` |
| `obligations/sbti_readiness.py` | Classify Category A/B; **version-aware** coverage math (V1.x 40%/67%/90% vs V2.0 per-category ≥5%); honest on unconfirmed net-zero % | Epic A `db/inventory_store.py` (`inventory_category_results` for the ≥5% denominator); `s1_consolidation` boundary concept |
| `obligations/cascade.py` | Detect customers that are themselves regulated → will cascade the request (P.1.4.b) | external enrichment (🔴 data-sourcing) |
| `db/obligation_store.py` | Persist profile + evaluated obligations | `db/store.py`, `db/org_store.py`, `shares_org_with` |

**Reuse:** company intake extends `gap_analyzer/models.py` `CompanyProfile` (add revenue/employees/EU-turnover/customers, persist it). Priority scoring (P.1.4.a) reuses gap_analyzer `assess_materiality`. Business-case narrative (P.1.1.d) reuses the RAG advisor pattern for grounded text — but the *obligations and dates come from the engine, not the LLM* (same numbers-looked-up discipline as Epic B §1).

---

## 5. API routes (`api/routes/obligations.py` — orchestrate only)

| Endpoint | Method | Does |
|---|---|---|
| `/api/company-profile` | POST/GET | Create/update the persisted org profile |
| `/api/obligations/evaluate` | POST | Run the engine → ranked obligations + timeline (P.1.1.b/.c) |
| `/api/obligations` | GET | List current obligations ("what's due when") |
| `/api/obligations/business-case` | GET | Why-now narrative grounded in the evaluated obligations (P.1.1.d) |
| `/api/obligations/sbti-readiness` | POST | Category A/B + coverage math for a given `inventory_id` (P.1.3) |
| `/api/obligations/cascade` | GET | Cascade-exposure list (P.1.4.b; may be stubbed/manual in MVP) |

---

## 6. Sub-phases (Goal · Files · Verify · Prompt)

### C1 — Company profile intake & store
- **Goal:** A persisted, org-level company profile with the fields the engine needs.
- **Files:** migration `058_company_profiles.sql`; `db/obligation_store.py` (profile CRUD); `POST/GET /api/company-profile`.
- **Verify:** Branch DB. Save a profile (revenue, employees, EU turnover, customers); read back org-scoped.
- **Prompt:** *Read §3. Create `058_company_profiles.sql` (RLS org-scoped like `027`). Extend the gap-analyzer `CompanyProfile` fields with `annual_revenue_usd`, `eu_turnover_eur`, `eu_subsidiary`, `employee_count`, `listed_status`, `key_customers`. Add profile CRUD to `db/obligation_store.py` and the `/api/company-profile` routes.*

### C2 — Obligation ruleset + engine  (P.1.1.b/.c)  ⭐ currency-critical
- **Goal:** A dated ruleset file and an engine that evaluates a profile into ranked, cited obligations with a timeline.
- **Files:** `data/obligation_rules/v2026-07.yaml` (seed from §2); `obligations/ruleset.py`; `obligations/engine.py`; migration `059_obligations.sql`; `POST /evaluate`, `GET /api/obligations`; `evals/fixtures/obligation_cases.json`.
- **Verify:** Seed rules match §2 exactly. A >$1B / >500-emp US consumer brand → SB253 (Scope 3 2027) + SBTi Category A (Scope 3 mandatory). Uncertain items (SB253 format, SB261 injunction) returned as `uncertain/watch`, not fixed. Determinism; `ruleset_version` recorded.
- **Prompt:** *Read §1, §2, §3. Create `data/obligation_rules/v2026-07.yaml` encoding the §2 table (predicate, due date, assurance, citation, confidence/status per rule). Create `obligations/ruleset.py` (schema-validated loader) and `obligations/engine.py` (evaluate a profile → ranked obligations + timeline, stamping `ruleset_version`). Encode the §1 uncertainty rule: unconfirmed/in-flux items return `applies: uncertain`, never a fabricated fixed value. Wire `POST /evaluate` and `GET /api/obligations`. Assert §7 invariants in `evals/fixtures/obligation_cases.json`.*

### C3 — Business-case / why-now  (P.1.1.d)
- **Goal:** A grounded narrative explaining, for this company, why to act and what's at stake.
- **Files:** `GET /api/obligations/business-case`.
- **Verify:** Narrative cites the evaluated obligations + deadlines (from the engine, not invented); flags uncertain items as watch, not fact.
- **Prompt:** *Read §4. Add `GET /api/obligations/business-case`: feed the evaluated obligations into the RAG advisor pattern to write a grounded why-now narrative. Dates and obligations come from the engine output; the LLM only phrases them. No invented deadlines.*

### C4 — SBTi readiness: Category A/B + coverage math  (P.1.3)  — depends on Epic A
- **Goal:** Classify the company A/B and compute version-aware Scope 3 coverage readiness against a real inventory.
- **Files:** `obligations/sbti_readiness.py`; `POST /api/obligations/sbti-readiness`.
- **Verify:** ICP (>$1B or >500 emp) → Category A → Scope 3 mandatory + base-year limited assurance flagged. **V2.0**: every Scope 3 category ≥5% of total needs a target (per-category, computed from Epic A `inventory_category_results`). **V1.x**: 40%/67%/90%. Net-zero % returns `unconfirmed` (not hardcoded). Version defaults to V2.0 for targets landing 2027+.
- **Prompt:** *Read §1, §2 (SBTi row), and `research/reg-status-verified.md` §5. Create `obligations/sbti_readiness.py`: classify Category A/B from the profile; compute version-aware coverage — V2.0 per-category ≥5% using Epic A `inventory_category_results` as the denominator, V1.x aggregate 67%/90%. Return the net-zero coverage % as `unconfirmed` per the research (do NOT hardcode). Flag base-year limited assurance as required for Category A. Wire `POST /sbti-readiness` (takes an `inventory_id`).*

### C5 — Priority scoring + cascade-exposure + evals  (P.1.4)
- **Goal:** Rank what matters; flag customers that will cascade the request; lock in invariants.
- **Files:** reuse gap_analyzer `assess_materiality` for P.1.4.a; `obligations/cascade.py`; `GET /api/obligations/cascade`; `tests/test_obligations.py`.
- **Verify:** Priority scoring returns a ranked list. Cascade detection flags a regulated customer (MVP: manual/list-based; enrichment later). All §7 invariants tested.
- **Prompt:** *Read §4 and §7. For P.1.4.a, call gap_analyzer `assess_materiality`. Create `obligations/cascade.py`: given `key_customers`, flag any that are themselves SB253/CSRD-caught (MVP: a maintained list + manual entry; external enrichment is a later fast-follow — research build-vs-buy says BUY the data). Wire `GET /cascade`. Write `tests/test_obligations.py` for §7.*

---

## 7. New eval invariants (ship a pytest with each)

- Every obligation carries a trigger predicate, threshold detail, and citation — no obligation without a backing rule.
- Items the research marks unconfirmed/in-flux (SBTi net-zero %, SB253 Scope 3 format, SB261 injunction) return `uncertain/watch` — never a fabricated fixed value.
- The ruleset is dated and versioned; every evaluation records the `ruleset_version` used.
- SBTi Category A classification is correct for the ICP (>$1B revenue OR >500 employees → Category A → Scope 3 mandatory).
- V2.0 per-category ≥5% coverage math is correct against a given inventory; net-zero % is reported as `unconfirmed`.
- Determinism: same profile + same ruleset → same obligations.

---

## 8. Risks & decisions

| Item | Type | Handling |
|---|---|---|
| Ruleset currency | 🟠 (the core risk) | Ruleset is a dated, versioned, git-reviewed data file (§1); staff a maintenance cadence. This is ongoing, not one-time. |
| Overstating certainty | 🔴 credibility | §1 uncertainty rule enforced as an invariant; unconfirmed items are watch-items, not obligations. |
| P.1.4.b cascade data sourcing | 🔴 | MVP = maintained list + manual entry; external obligation-signal enrichment (D&B/filings) is a later BUY (research build-vs-buy). |
| SBTi version transition (V1.3.1 vs V2.0) | 🟠 | Version-aware; default V2.0 for targets landing 2027+, offer V1.3.1 only in the transition window (to 31 Jan 2028). |
| Dependency on Epic A | 🟠 | C4 coverage math needs a real inventory; C1–C3 are independent and can ship before A completes. |
| Not legal advice | 🟢 | Frame as a screening tool with citations; recommend legal confirmation for edge cases. |

---

## 9. Definition of done

A company fills in its profile (revenue, employees, EU exposure, key customers) and immediately gets: a **ranked list of the obligations that actually bite** (e.g., "SB253 — Scope 3 from 2027; SBTi Category A — Scope 3 targets mandatory + base-year assurance"), a **timeline of what's due when**, a **grounded why-now business case**, and — once they have an Epic A inventory — a **Category A/B classification with per-category ≥5% coverage readiness**. Every line cites its rule; every moving/unconfirmed item is honestly flagged as a watch. Customer-request obligations route straight into Epic B. Together, Epics A + B + C are the research's MVP: *know your obligation → get a defensible number → answer the customer.*
