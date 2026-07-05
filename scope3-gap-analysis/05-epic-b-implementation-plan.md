# Implementation Plan — Epic B: Inbound Request → Questionnaire Answer

**Branch:** `feature/scope3-mvp`
**Status:** Plan, pre-implementation
**Source:** `03-enhancement-roadmap.md` Epic B (Big bet 2). Depends on Epic A (`04-epic-a-implementation-plan.md`) for the company number.

> **What this epic is.** The research's #1 wedge and emotional buying trigger — **JTBD-1: "answer the customer without a data team."** A retailer/customer/CDP/EcoVadis request lands; the platform captures it, detects its framework, maps its questions to the corporate inventory (Epic A) and product footprints, drafts credible answers, and exports them. This is what turns CarbonOS from "a footprint tool" into "the thing you buy when Walmart emails you."

> **What this epic is NOT.** Not formal audited disclosure generation (ESRS/SB253 iXBRL — that's Epic G). Not a number *generator* — it is a number *router*: every figure comes from an existing datapoint, never from the LLM. Narrative is generated and grounded; numbers are looked up.

Research units closed: **P.1.2.a/.b/.c** (inbound request capture → task → handoff), **P.4.2.1** (intake & framework detection — 🔴 classifier), **P.4.2.2** (question→datapoint mapping — 🔴 the join), **P.4.2.3** (category relevance-status), **P.4.2.4** (methodology narrative), **P.4.2.5** (answer assembly & review), **P.4.2.6.b/.c** (EcoVadis/retailer + generic export), **P.4.2.7** (answer library & reuse).

---

## 1. The trust constraint (read first — it governs the whole design)

The research flags P.4.2.1/.2 as **trust-defining**: an auto-drafted answer is only valuable if the analyst can submit it to a customer without fear. One hallucinated emissions number destroys the product. So the non-negotiable rule, enforced as an eval invariant:

> **Numbers are looked up, never generated.** Every numeric answer resolves to a specific datapoint (an Epic A `inventory_category_results` row, an `inventory_versions.total`, or a product footprint field) or a prior `answer_library` entry — with a citation. Anything that cannot be mapped is **flagged "needs human input," not guessed.** The LLM writes *narrative* (methodology text, qualitative answers) grounded in RAG; it does not invent figures.

This mirrors the existing advisor eval rubric ("no fabricated numbers") — Epic B extends it from chat to submitted answers.

---

## 2. Conceptual flow

```
Customer request         Detect framework        Map questions            Assemble + review        Export / submit
(email / upload)    ──►   + parse question   ──►  → datapoints       ──►   draft answers      ──►   EcoVadis / retailer /
                          set (P.4.2.1 🔴)        (P.4.2.2 🔴)              + methodology            generic PDF/CSV
   │                                               │                        + category status         + save to library
   ▼                                               ▼                        (human checkpoint)              │
questionnaire_requests                    Epic A inventory ────────────────────────────────────────────────┘
(extends pcf_requests inbox)              + product footprints                                    answer_library (reuse)
```

Handoff in: Epic C's request-signal capture (P.1.2) routes a captured request here (P.1.2.c). Handoff data source: Epic A's locked inventory version.

---

## 3. New data model (migrations `034`–`037`)

Extends the existing inbound-inbox pattern in `027_pcf_requests.sql` (which handles *product-footprint share* requests) to *questionnaire* requests. RLS mirrors `pcf_requests` (org-member scoped).

| Table | Purpose | Key columns |
|---|---|---|
| `questionnaire_requests` | An inbound questionnaire to answer | `request_id`, `org_id`, `customer_name`, `framework` (`cdp`/`ecovadis`/`walmart`/`tesco_cdf`/`generic`), `source_file`, `deadline`, `status` (`open`/`in_progress`/`submitted`/`declined`), `inventory_id` (the Epic A version answered from) |
| `questionnaire_questions` | Parsed questions | `question_id`, `request_id`, `section`, `question_text`, `question_type` (`numeric`/`boolean`/`select`/`narrative`), `framework_field_key` |
| `question_datapoint_mappings` | Question → datapoint + drafted answer | `mapping_id`, `question_id`, `datapoint_ref` (e.g. `inventory:cat1.total`), `mapped_value`, `answer_text`, `confidence_score`, `method`, `citation`, `flag_status` |
| `answer_library` | Reusable prior answers (compounding moat) | `answer_id`, `org_id`, `framework_field_key`, `question_signature`, `answer_text`, `source_request_id`, `last_used_at` |

---

## 4. New modules (business logic — no UI imports)

| Module | Responsibility | Reuses |
|---|---|---|
| `questionnaire/framework_detector.py` | Detect framework + parse its question set. Per-framework templates for known formats (CDP/EcoVadis/CDF); generic fallback parser. **🔴 classifier.** | `factors/ef_lookup.py` `_find_sector` fuzzy matcher (for question/field matching); `parsing/` conventions |
| `questionnaire/question_mapper.py` | Map each question to a datapoint (Epic A inventory / product footprint / library) + confidence + flag. **🔴 the join.** Enforces §1 (numbers looked up, never generated). | Epic A `db/inventory_store.py` results; `db/rollup_store.py`; `answer_library` |
| `questionnaire/answer_assembler.py` | Assemble draft answers; generate methodology narrative (grounded); attach category relevance-status | `pages/1_Advisor.py`/RAG advisor for narrative; gap_analyzer `assess_reporting_requirements` structured output for P.4.2.3 |
| `questionnaire/exporters/` | EcoVadis/retailer packs + generic PDF/CSV | `exchange/pact.py` serialization patterns; `api/routes/shares.py`, `public.py` |
| `db/questionnaire_store.py` | CRUD for the 4 tables | `db/request_store.py`, `db/store.py`, `shares_org_with` |

**Reuse insight:** the gap analyzer already answers "which of the 15 categories apply to this company" with a structured `{applicable, not_applicable, uncertain}` payload (`gap_analyzer/tools/assess_reporting_requirements.py`). That *is* the category relevance-status answer (P.4.2.3) most questionnaires ask for — reuse it directly rather than rebuild.

---

## 5. API routes (`api/routes/questionnaire.py` — orchestrate only)

Follows the BOM analyzer's human-in-the-loop checkpoint pattern (detect → map → **review** → assemble → export).

| Endpoint | Method | Does |
|---|---|---|
| `/api/questionnaires` | POST/GET | Create inbound request (upload file or manual) / list |
| `/api/questionnaires/{id}/detect` | POST | Framework detection + question parsing → `questionnaire_questions` |
| `/api/questionnaires/{id}/map` | POST | Map questions to datapoints against a chosen `inventory_id`; low-confidence + unmappable flagged |
| `/api/questionnaires/{id}` | GET | Review draft answers with confidence, citations, flags |
| `/api/questionnaires/{id}/answers/{qid}` | PATCH | Analyst edit/override of an answer |
| `/api/questionnaires/{id}/assemble` | POST | Assemble final answers + methodology narrative + category status |
| `/api/questionnaires/{id}/export` | POST | Export (format param: `ecovadis`/`retailer`/`pdf`/`csv`) |
| `/api/questionnaires/{id}/submit` | POST | Mark submitted; write answers to `answer_library` |

---

## 6. Sub-phases (Goal · Files · Verify · Prompt)

### B1 — Data model & store
- **Goal:** 4 tables + store; no detection/mapping yet.
- **Files:** migrations `034`–`037`; `db/questionnaire_store.py`.
- **Verify:** Branch DB. Create a request, add questions, read back org-scoped. RLS blocks cross-org.
- **Prompt:** *Read §3. Create migrations 034–037 following the RLS pattern in `027_pcf_requests.sql`. Create `db/questionnaire_store.py` mirroring `db/request_store.py`. No AI logic yet.*

### B2 — Inbound request intake  (P.1.2.a/.b/.c)
- **Goal:** Capture a questionnaire request (upload or manual), set a deadline/task, accept a handoff from Epic C.
- **Files:** `POST/GET /api/questionnaires`; extend intake to accept a payload from P.1.2 request-signal capture.
- **Verify:** Create a request with a deadline; it appears in the org inbox; a Epic-C handoff payload creates one.
- **Prompt:** *Read §2. Wire `POST /api/questionnaires` to create a `questionnaire_requests` row (file upload → storage, or manual fields), extending the inbox pattern from `db/request_store.py`. Accept an optional handoff payload (customer, framework hint, deadline) so Epic C's P.1.2.c can route into it.*

### B3 — Framework detection & question parsing ⭐  (P.4.2.1)
- **Goal:** From an uploaded questionnaire, detect the framework and extract a structured question set.
- **Files:** `questionnaire/framework_detector.py`; per-framework templates `questionnaire/templates/{cdp,ecovadis,cdf}.py`; `POST /detect`; labeled fixtures `evals/fixtures/framework_detection_cases.json`.
- **Verify:** **Prototype against labeled real questionnaires before the UI** (research instruction for 🔴 classifiers). Correct framework detected; questions parsed with `question_type`; generic fallback works; low-confidence flagged.
- **Prompt:** *Read §1 and §4. Create `questionnaire/framework_detector.py`: given an uploaded questionnaire, detect framework (CDP/EcoVadis/Walmart/Tesco CDF/generic) and parse questions into `questionnaire_questions` with `question_type` and `framework_field_key`. Use per-framework templates for known formats; generic parser as fallback. Build `evals/fixtures/framework_detection_cases.json` and validate accuracy before wiring `POST /detect`.*

### B4 — Question → datapoint mapping ⭐  (P.4.2.2) — the trust-critical join
- **Goal:** Each question mapped to a datapoint + drafted value, honoring §1 (numbers looked up, never generated).
- **Files:** `questionnaire/question_mapper.py`; `POST /map`; `PATCH /answers/{qid}`; `evals/fixtures/question_mapping_cases.json`.
- **Verify:** Numeric answers equal the underlying Epic A datapoint exactly. Unmappable questions flagged "needs human input," never fabricated. Low-confidence flagged. Override recomputes. Determinism.
- **Prompt:** *Read §1 (non-negotiable), §3, §4. Create `questionnaire/question_mapper.py`: map each `questionnaire_question` to a datapoint ref (`inventory:catN.total`, `inventory:total`, product footprint field, or `answer_library`). Populate `mapped_value`/`answer_text`/`citation`/`confidence`. Numeric values are LOOKED UP from `db/inventory_store.py` — never LLM-generated. Anything unmappable → `flag_status='needs_human'`. Wire `POST /map` and the override `PATCH`. Assert the no-fabrication invariant in `evals/fixtures/question_mapping_cases.json`.*

### B5 — Assembly + methodology narrative + category status  (P.4.2.3/.4/.5)
- **Goal:** A reviewable draft: answers + grounded methodology text + category relevance-status.
- **Files:** `questionnaire/answer_assembler.py`; `POST /assemble`; `GET /{id}` review view.
- **Verify:** Methodology narrative is RAG-grounded (cites GHG Protocol, no fabricated numbers). Category status comes from the gap-analyzer output. Human checkpoint before export.
- **Prompt:** *Read §4. Create `questionnaire/answer_assembler.py`: combine mapped answers, generate a grounded methodology narrative via the RAG advisor pattern (`llm/`+`rag/`), and attach category relevance-status by calling gap_analyzer `assess_reporting_requirements`. Wire `POST /assemble` and the `GET` review view showing confidence + citations + flags.*

### B6 — Export + answer library + submit + evals  (P.4.2.6/.7)
- **Goal:** Export a submittable pack; reuse answers next time.
- **Files:** `questionnaire/exporters/`; `POST /export`, `POST /submit`; `tests/test_questionnaire.py`.
- **Verify:** EcoVadis/retailer + generic PDF/CSV export validate. On submit, answers land in `answer_library` and are offered on the next matching question. All §7 invariants tested.
- **Prompt:** *Read §4 and §7. Create `questionnaire/exporters/` (ecovadis, retailer, pdf, csv) reusing `exchange/` and `shares.py` patterns. On `POST /submit`, write answers to `answer_library` keyed by `framework_field_key`/`question_signature`; the mapper (B4) checks the library first next time. Write `tests/test_questionnaire.py` for every §7 invariant.*

---

## 7. New eval invariants (ship a pytest with each)

- **No fabricated numbers:** every numeric answer resolves to a datapoint ref or library entry with a citation; nothing numeric is LLM-generated.
- Numeric answer == underlying inventory/footprint datapoint (no silent transformation).
- Unmappable questions are flagged `needs_human`, never auto-filled.
- Low-confidence framework detection / mapping flagged for review.
- Every answer carries a source citation and/or methodology reference.
- Methodology narrative is RAG-grounded (extends the advisor "grounded, no fabricated numbers" rubric).
- Submitted answers are written to `answer_library`; reused answers cite the prior submission.

---

## 8. Risks & decisions

| Item | Type | Handling |
|---|---|---|
| Two 🔴 classifiers (detection B3, mapping B4) | 🔴 | Prototype both against labeled real questionnaires before UI (research instruction). |
| Hallucinated numbers | 🔴 trust | §1 rule enforced as eval invariant — numbers looked up, never generated. The single most important constraint in this epic. |
| Framework format drift (yearly) | 🟠 | Template-based + versioned per framework; research flags P.4.2.6 as *ongoing maintenance, not one-time*. Staff for it. |
| CDP / EcoVadis often have no API | 🟠 | Export a semi-manual submission pack (PDF/CSV/portal-paste), not a live API push — per research build-vs-buy. CDP API export is a V1 fast-follow (P.4.2.6.a). |
| Dependency on Epic A | 🟠 | B4 needs a locked inventory version. Can demo against product footprints alone if A is incomplete, but full value needs A's company number. Sequence A before B. |

---

## 9. Definition of done

A 2-person team receives a Walmart/CDP/EcoVadis questionnaire → uploads it → the platform detects the framework, maps its questions to their locked corporate inventory, and drafts answers with citations and confidence → the analyst reviews, fixes the flagged gaps, and exports a submittable pack — **in under two weeks, no consultant.** That is the research's stated MVP win condition (`research/synthesis.md`), and Epics A + B together are what deliver it.
