# Implementation Plan — Epic G: Formal Disclosure Generation

**Branch:** `feature/scope3-mvp`
**Status:** Plan, pre-implementation
**Source:** `03-enhancement-roadmap.md` Epic G; `00-program-overview.md` §2. Depends on **Epic A** (inventory to disclose). **Reverses a current CarbonOS non-goal** ("does not prepare a regulatory or compliance report") — see §8.

> **What this epic is.** The research's **JTBD-6: "produce the one artifact I'm actually on the hook for."** Generate a formal, audit-grade disclosure from the corporate inventory: ESRS E1 (with iXBRL tagging), California SB 253, and IFRS S2 — plus a board/investor climate report. Turns the inventory into the specific filed document a regulator or investor demands.

> **What this epic is NOT.** Not the customer/questionnaire answer (that's Epic B — a lighter, non-audited artifact). Not assurance itself — it produces the *assurance-ready pack* (methodology, lineage) that an external assurer signs; it does not self-certify. Not a substitute for legal/audit review.

Research units closed: **P.4.1.a** (datapoint mapping), **P.4.1.b** (narrative + quant assembly), **P.4.1.c** (iXBRL / CARB / format output), **P.4.6.c** (board/investor climate reporting). Adjacent: **P.4.3** assurance pack (methodology/lineage) is largely satisfied by Epic A's existing `audit_log`/citation lineage — surfaced here.

---

## 1. The currency + honesty constraint (read first)

Disclosure formats are the most volatile, highest-stakes surface in the program. Enforced as invariants:

1. **Formats are versioned data, not code** — ESRS taxonomy and the SB253 schema live as dated, versioned mapping specs; every generated filing records the format version used. (Same discipline as the obligation ruleset in Epic C.)
2. **SB 253 Scope 3 output is explicitly provisional.** Per `research/reg-status-verified.md` §4, CARB's final SB253 regulation is expected ~end-2026 with the **Scope 3 report format still open** (three applicability options). The SB253 generator emits a **clearly-labeled provisional draft** and refuses to imply a final, filed format until the CARB reg lands. Never present an unfinalized format as authoritative.
3. **Numbers looked up, never generated** — every disclosed figure resolves to an Epic A datapoint with lineage; the LLM writes only the qualitative narrative (governance, transition, methodology text), grounded. This mirrors `exchange/pact.py`'s existing "serialize, don't invent" posture.
4. **iXBRL tagging is bought, not built** — per the research build-vs-buy call, integrate an existing ESEF/iXBRL tagging library; build only the datapoint→tag mapping.

---

## 2. What gets mapped (inventory → framework datapoints)

| Framework | Key datapoints | Format |
|---|---|---|
| **ESRS E1** | E1-6 Gross Scopes 1/2/3 + Total GHG; methodology & DQ disclosure; value-chain coverage | iXBRL (ESEF taxonomy) in the management report |
| **CA SB 253** | Annual Scope 1&2 (2026) + **Scope 3 (2027)**; assurance status | CARB format (**provisional** — see §1.2) |
| **IFRS S2 / ISSB** | Scope 3 per GHG Protocol; cross-industry metrics; transition reliefs | ISSB structured output |
| **Board / investor** | Totals, targets (Epic D), progress (Epic E), risk | Narrative report / deck |

All four draw from **one** Epic A inventory — the "conflict" between frameworks is presentation/datapoint mapping, not measurement (all defer to GHG Protocol). A single conformant inventory feeds every output via a mapping layer.

---

## 3. New data model (migrations `048`–`049`)

| Table | Purpose | Key columns |
|---|---|---|
| `disclosures` | A generated disclosure | `disclosure_id`, `org_id`, `framework` (`esrs_e1`/`sb253`/`ifrs_s2`/`board`), `inventory_id`, `format_version`, `status` (`draft`/`provisional`/`final`), `is_provisional`, `generated_at` |
| `disclosure_datapoints` | Mapped datapoint values | `disclosure_id`, `datapoint_key`, `value`, `source_ref`, `xbrl_tag` |

Framework mapping specs live as versioned files: `data/disclosure_specs/{framework}/{version}.yaml`.

---

## 4. New modules (business logic — no UI imports)

| Module | Responsibility | Reuses |
|---|---|---|
| `disclosure/datapoint_mapper.py` | Map inventory → framework datapoints per the versioned spec | Epic A `db/inventory_store.py`; Epic D targets; Epic E progress |
| `disclosure/assembler.py` | Assemble narrative + quantitative disclosure | RAG advisor (grounded narrative); `audit_log`/citation lineage |
| `disclosure/exporters/ixbrl.py` | iXBRL tagging via a bought tagging lib | **integrate** ESEF/iXBRL library; `exchange/pact.py` serialization discipline |
| `disclosure/exporters/{sb253,ifrs_s2,board}.py` | Provisional SB253 / IFRS S2 / board outputs | `exchange/`, `s1_reporting/report.py` assembly pattern |
| `db/disclosure_store.py` | CRUD | `db/store.py`, `db/inventory_store.py` |

---

## 5. API routes (`api/routes/disclosure.py` — orchestrate only)

| Endpoint | Method | Does |
|---|---|---|
| `/api/disclosures/map` | POST | Map an `inventory_id` to a framework's datapoints |
| `/api/disclosures` | POST/GET | Generate / list disclosures |
| `/api/disclosures/{id}/export` | POST | Export (iXBRL / provisional SB253 / IFRS S2 / board pack) |
| `/api/disclosures/{id}/assurance-pack` | POST | Methodology + lineage pack (surfaces Epic A P.4.3) |

---

## 6. Sub-phases

### G1 — Datapoint mapping  (P.4.1.a)
- **Goal:** Versioned framework specs + a mapper from inventory to datapoints.
- **Verify:** ESRS E1-6 Scopes 1/2/3 + Total map correctly from Epic A; every value carries a `source_ref`. Format version recorded.
- **Prompt:** *Read §1, §2, §3. Create `data/disclosure_specs/esrs_e1/v1.yaml` (start with E1-6) and `disclosure/datapoint_mapper.py`. Map Epic A inventory + Epic D/E outputs to datapoints; stamp `format_version`; every value gets a `source_ref`. Wire `POST /api/disclosures/map`.*

### G2 — Narrative + quant assembly  (P.4.1.b)
- **Goal:** Assemble a full disclosure (grounded narrative + mapped quant).
- **Verify:** Narrative is RAG-grounded; all figures come from mapped datapoints (none LLM-generated); methodology text cites lineage.
- **Prompt:** *Read §1.3, §4. Create `disclosure/assembler.py`: combine mapped datapoints with a grounded narrative (governance/methodology/transition) via the RAG advisor; numbers strictly from datapoints. Wire `POST /api/disclosures`.*

### G3 — iXBRL + provisional SB253 + IFRS S2 + board  (P.4.1.c, P.4.6.c)
- **Goal:** Format outputs, with SB253 clearly provisional.
- **Verify:** iXBRL validates against the ESEF taxonomy (via the bought lib). SB253 output is labeled `provisional` and refuses to claim final format. Board pack renders totals/targets/progress.
- **Prompt:** *Read §1.2, §1.4, §4. Create `disclosure/exporters/ixbrl.py` integrating a bought ESEF/iXBRL tagging library (map datapoint→tag; do not hand-roll tagging). Create `sb253.py` (emit `is_provisional=true`, labeled draft, per §1.2), `ifrs_s2.py`, and `board.py`. Wire `POST /api/disclosures/{id}/export`.*

### G4 — Assurance pack + evals  (P.4.3 surfaced)
- **Goal:** Methodology + lineage pack; lock invariants.
- **Verify:** Pack assembles from Epic A `audit_log`/citations; `tests/test_disclosure.py` covers §7.
- **Prompt:** *Read §4, §7. Create `disclosure/` assurance-pack assembly from Epic A lineage. Wire `POST /assurance-pack`. Write `tests/test_disclosure.py`.*

---

## 7. New eval invariants

- Every disclosed figure resolves to an Epic A datapoint with a `source_ref`; no LLM-generated numbers.
- Disclosure records its `format_version`; format specs are versioned data.
- SB253 Scope 3 output is emitted `is_provisional=true` and labeled draft until the CARB final reg is encoded.
- iXBRL output validates against the ESEF taxonomy via the integrated tagging library.
- Narrative is RAG-grounded; methodology text cites lineage.

---

## 8. Risks & decisions

| Item | Type | Handling |
|---|---|---|
| **Reverses the "no compliance report" non-goal** | decision | Full-platform aspiration requires it; confirm as a deliberate scope/GTM expansion. Largest single scope change in the program. |
| SB253 format not final (~end-2026) | 🔴🟠 | Provisional output only (§1.2); encode the final CARB format when it lands. |
| ESRS taxonomy + format drift | 🟠 | Versioned specs (§1.1); ongoing maintenance headcount. |
| iXBRL complexity | 🟠 | Buy/integrate a tagging library; don't build. |
| Not assurance/legal sign-off | 🟢 | Produces the assurance-ready pack; external assurer + legal review still required. |

---

## 9. Definition of done

An analyst with a locked Epic A inventory (and Epic D targets / Epic E progress) generates: an **ESRS E1 disclosure with valid iXBRL tagging**, a **provisional, clearly-labeled SB253 report**, an **IFRS S2 output**, and a **board/investor pack** — every number traced to the inventory, every format version recorded, the SB253 draft honestly marked provisional, and an **assurance-ready methodology + lineage pack** an external assurer can sign. The platform now produces the audited artifact, not just the customer answer.
