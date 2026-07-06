# Implementation Plan — Epic F: Supplier Engagement at Program Scale

**Branch:** `feature/scope3-mvp`
**Status:** Plan, pre-implementation
**Source:** `03-enhancement-roadmap.md` Epic F; `00-program-overview.md` §2. Reuses the **existing `copilot` primary-data loop heavily**; Epic A sharpens corporate hotspot targeting. Largely independent of B/C/D — can start early.

> **What this epic is.** The research's **JTBD-5: "move the suppliers we can't control."** Scale CarbonOS's already-working single-supplier engagement loop into a *program*: cohort suppliers by emissions/spend, run cascaded request campaigns, collect PCFs at scale, and track scorecards + supplier-SBT status. This is the research's **most defensible moat** — collected supplier data compounds and is expensive for a competitor to re-gather.

> **What this epic is NOT.** Not a new engagement engine — the loop (`copilot/exception_router.py` `STORE_DATA` → line-item recalc → PDS) already exists and works. Epic F is **orchestration and scale** on top of it. Not per-supplier deep abatement (low-leverage mid-market can't do that — the research explicitly prefers supplier-SBT/engagement targets instead).

Research units closed: **P.3.4.a** (supplier cohorting/campaigns), **P.3.4.b** (PCF collection orchestration = P.2.3.c at program scale), **P.3.4.c** (scorecards & supplier-SBT tracking), **P.2.3.a** (hotspot deepening prioritization) at corporate scale.

---

## 1. The "scale an existing loop, don't rebuild" constraint (read first)

Epic F is the highest-confidence epic in the program because it is mostly reuse. Two rules keep it that way:

1. **The unit of work stays the existing loop.** Per-supplier: rank (`copilot/suppliers_list.py`) → draft request (`copilot/draft_email.py`) → parse response (`copilot/parse_response.py`) → route (`copilot/exception_router.py`: `STORE_DATA`/`NUDGE`/`ESCALATE`) → primary data updates the footprint and raises PDS. Epic F wraps *many* of these into a campaign; it does not replace the loop.
2. **Collected primary data flows back into the inventory.** A PCF collected via a campaign must update the underlying footprint/line item and therefore the Epic A corporate inventory and PDS — closing the loop to measurement. This is the moat: engagement improves the number, not just a CRM record.

---

## 2. Conceptual flow

```
Epic A corporate hotspots ──► cohort suppliers by emissions/spend ──► campaign (cascaded requests, deadline)
   (P.2.3.a / P.3.4.a)                                                      │
                                                                            ▼
                        per supplier: existing loop  rank→draft→parse→ROUTE (STORE_DATA/NUDGE/ESCALATE)
                                                                            │ STORE_DATA
                                                                            ▼
                            PCF updates footprint → Epic A inventory + PDS ↑ (loop closed to measurement)
                                                                            │
                                                     scorecards + supplier-SBT tracking (P.3.4.c)
```

---

## 3. New data model (migrations `045`–`047`)

Extends the existing `supplier_engagements` (002) + `engagement_primary_outcome` (022) rather than replacing them.

| Table | Purpose | Key columns |
|---|---|---|
| `supplier_campaigns` | A cohorted engagement campaign | `campaign_id`, `org_id`, `name`, `cohort_basis` (`emissions`/`spend`), `request_template`, `deadline`, `status` |
| `campaign_suppliers` | Campaign membership + per-supplier status | `campaign_id`, `supplier_id`, `engagement_id`, `status` (`pending`/`sent`/`responded`/`stored`/`escalated`), `pcf_received` |
| `supplier_scorecards` | Per-supplier scorecard | `supplier_id`, `org_id`, `coverage_pct`, `pcf_count`, `avg_dq`, `supplier_sbt_status`, `updated_at` |

---

## 4. New modules (business logic — no UI imports)

| Module | Responsibility | Reuses |
|---|---|---|
| `engagement/cohorting.py` | Rank + group suppliers by emissions/spend into a target cohort | **`copilot/suppliers_list.py`** ranking; Epic A corporate hotspots |
| `engagement/campaign.py` | Orchestrate the cascade across a cohort; drive each supplier through the existing loop; aggregate status | **`copilot/exception_router.py`** loop; `draft_email`, `parse_response` |
| `engagement/scorecard.py` | Compute per-supplier scorecards + supplier-SBT tracking (P.3.4.c) | stored PCFs; `calc/dqr.py`; PDS |
| `db/campaign_store.py` | CRUD | `db/store.py`, existing engagement stores |

---

## 5. API routes (`api/routes/campaigns.py` — orchestrate only)

| Endpoint | Method | Does |
|---|---|---|
| `/api/campaigns/cohort` | POST | Given corporate hotspots → ranked supplier cohort proposal |
| `/api/campaigns` | POST/GET | Create / list campaigns |
| `/api/campaigns/{id}/send` | POST | Kick off cascaded requests across the cohort (drafts via existing loop) |
| `/api/campaigns/{id}` | GET | Campaign status board (per-supplier states) |
| `/api/suppliers/{id}/scorecard` | GET | Supplier scorecard + supplier-SBT status |

---

## 6. Sub-phases

### F1 — Cohorting  (P.3.4.a / P.2.3.a)
- **Goal:** Turn corporate hotspots into a ranked, grouped supplier cohort.
- **Verify:** Cohort ordering matches emissions/spend ranking; reuses `suppliers_list` scoring, not a new ranker.
- **Prompt:** *Read §1, §4. Create `engagement/cohorting.py`: rank suppliers via `copilot/suppliers_list.py`, grouped by Epic A corporate hotspot categories, into a cohort ordered by emissions or spend. Wire `POST /api/campaigns/cohort`. Deterministic ordering.*

### F2 — Campaign orchestration  (P.3.4.a/.b)
- **Goal:** Run cascaded requests across a cohort, each supplier driven through the existing loop; aggregate status.
- **Verify:** A campaign drafts requests for all cohort members; responses route via `exception_router`; `STORE_DATA` outcomes update the footprint (loop closed). Status board reflects per-supplier state.
- **Prompt:** *Read §1 (the loop must stay the unit of work), §2, §3. Create `engagement/campaign.py`: create a campaign over a cohort; for each supplier use `copilot/draft_email.py` → on response `copilot/parse_response.py` + `exception_router.py`; ensure `STORE_DATA` writes primary data to the footprint (Epic A inventory + PDS). Wire `POST /api/campaigns`, `/send`, and the `GET` status board.*

### F3 — Scorecards + supplier-SBT tracking  (P.3.4.c)
- **Goal:** Per-supplier scorecards and supplier-SBT status.
- **Verify:** Scorecard coverage/PDS/DQ trace to stored PCFs; supplier-SBT status tracked and reportable (supports Epic D's supplier-engagement target type).
- **Prompt:** *Read §4. Create `engagement/scorecard.py`: compute per-supplier coverage %, PCF count, avg DQ (`calc/dqr.py`), and supplier-SBT status from stored data. Wire `GET /api/suppliers/{id}/scorecard`.*

### F4 — Evals
- **Prompt:** *Write `tests/test_campaigns.py` for §7 — especially that campaign-collected PCFs update the inventory + PDS (loop closed).*

---

## 7. New eval invariants

- Cohort ordering is deterministic and matches the `suppliers_list` emissions/spend ranking.
- A campaign drives each supplier through the existing `exception_router` loop (no parallel engagement logic).
- A `STORE_DATA` outcome in a campaign updates the underlying footprint → Epic A inventory → PDS rises (loop closed to measurement).
- Scorecard metrics (coverage, PDS, DQ) trace to stored PCF records; no fabricated values.
- Supplier-SBT status is tracked per supplier (feeds Epic D supplier-engagement targets).

---

## 8. Risks & decisions

| Item | Type | Handling |
|---|---|---|
| Low mid-market supplier leverage | 🟠 (design) | Prefer supplier-SBT/engagement targets over deep per-supplier abatement (research); integrate collective rails (retailer CDF, CDP Supply Chain, EcoVadis) as the realistic channel. |
| Supplier UX / response rates | 🟠 | The existing loop already handles NUDGE/ESCALATE; campaign adds reminders/deadlines. A supplier portal is a later enhancement. |
| Mostly reuse | 🟢 | Highest-confidence epic — do not rebuild the loop; wrap it. |
| Benefits from Epic A | 🟠 | Corporate hotspots sharpen cohort targeting, but F can run on product-level hotspots if A is incomplete. |

---

## 9. Definition of done

An analyst selects a hotspot category, gets a **ranked supplier cohort**, launches a **campaign** that cascades requests across it, and watches responses flow through the existing loop so that **each collected PCF raises the corporate inventory's PDS** — while **scorecards** track per-supplier coverage and **supplier-SBT status** feeds the Epic D target. The engagement moat now compounds: every campaign makes the number more primary-data-backed and more defensible.
