# Implementation Plan — Epic E: Progress Tracking + Base-Year Recalculation

**Branch:** `feature/scope3-mvp`
**Status:** Plan, pre-implementation
**Source:** `03-enhancement-roadmap.md` Epic E; `00-program-overview.md` §2. Depends on **Epic A** (InventoryVersions) and **Epic D** (Target trajectory).

> **What this epic is.** The research's **JTBD-7: "improve next year and prove it was real."** Track the inventory against the target trajectory year over year, run the GHG Protocol base-year recalculation policy when structural changes occur, and — critically — **distinguish real reductions from method/data-driven changes.** This is what makes the platform the *annual* system of record rather than a one-time calculator.

> **What this epic is NOT.** Not target-*setting* (Epic D). Not formal disclosure output (Epic G) — though it feeds the progress narrative Epic G/CDP consume. Not scenario/what-if modeling of future levers (Epic I).

Research units closed: **P.3.6.a** (progress tracking vs trajectory), **P.3.6.b** (base-year recalculation), **P.4.4.b** (progress disclosure/narrative), **P.3.1.a/.b** at corporate altitude (year-over-year hotspot movement).

---

## 1. The "real vs. method" constraint (read first)

The entire credibility of a progress claim rests on one distinction, enforced as an eval invariant:

> **A year-over-year change is decomposed into (a) real reductions/increases and (b) method/data-driven changes** (new EF version, spend→activity deepening, boundary change, restatement). Only (a) counts toward the target. A drop caused by switching to a better emission factor is **not** a reduction and must never be reported as one.

This drives the base-year recalculation policy: structural changes (M&A, methodology changes, significant restatements) above a significance threshold trigger a base-year recalculation so the trajectory compares like with like. Below threshold → no recalc (avoids churn). The threshold and the recalc are recorded with rationale.

Corollary (shared discipline): **numbers looked up, not generated** — deltas come from comparing Epic A `InventoryVersion`s; the LLM only narrates.

---

## 2. Conceptual flow

```
InventoryVersion(t0=base) ──┐
InventoryVersion(t1) ───────┼──► decompose Δ ──► real Δ ──► track vs Target trajectory (Epic D) ──► on/off track
InventoryVersion(t2) ───────┘        │                                                              │
                                     └──► method/data Δ ──► base-year recalc? (if structural > threshold) ──┘
                                                                                                    │
                                                                              progress narrative (grounded) ──► Epic G / CDP
```

---

## 3. New data model (migrations `043`–`044`)

| Table | Purpose | Key columns |
|---|---|---|
| `target_progress` | A progress snapshot vs trajectory | `progress_id`, `org_id`, `target_id`, `inventory_id`, `period`, `actual_total`, `trajectory_total`, `real_delta`, `method_delta`, `status` (`on_track`/`off_track`) |
| `base_year_recalcs` | A recorded base-year recalculation | `recalc_id`, `org_id`, `trigger` (`ma`/`method`/`restatement`), `significance_pct`, `threshold_pct`, `old_base_total`, `new_base_total`, `rationale`, `recalc_at` |

Extend `inventory_versions` (Epic A) with `is_base_year` and `base_year_recalc_id`.

---

## 4. New modules (business logic — no UI imports)

| Module | Responsibility | Reuses |
|---|---|---|
| `progress/decompose.py` | Compare two InventoryVersions → split Δ into real vs method/data | Epic A `db/inventory_store.py` lineage; EF version metadata |
| `progress/tracker.py` | Actual vs Epic D trajectory → on/off-track; corporate hotspot movement | Epic D `targets`; hotspot computation |
| `progress/recalc.py` | GHG Protocol base-year recalc policy + significance threshold | product versioning/recalc pattern; V2.0 single/physical base-year rule |
| `progress/narrative.py` | Grounded progress narrative (P.4.4.b) | RAG advisor pattern; the decomposed deltas |
| `db/progress_store.py` | CRUD | `db/store.py`, `db/inventory_store.py` |

**Reuse insight:** CarbonOS already recalculates a footprint into a new version on new data (product altitude). Epic E lifts that exact pattern to the corporate InventoryVersion and adds the *real-vs-method decomposition* and the *significance threshold* the corporate policy requires.

---

## 5. API routes (`api/routes/progress.py` — orchestrate only)

| Endpoint | Method | Does |
|---|---|---|
| `/api/progress/track` | POST | Given `target_id` + `inventory_id` → snapshot with real/method decomposition + on/off-track |
| `/api/progress` | GET | Progress history for a target |
| `/api/progress/recalc` | POST | Evaluate a structural change; recalc base year if above threshold |
| `/api/progress/narrative` | GET | Grounded progress narrative for a period |

---

## 6. Sub-phases

### E1 — Δ decomposition (real vs method)  ⭐ credibility-critical  (part of P.3.6.a)
- **Goal:** Given two InventoryVersions, split the change into real vs method/data-driven.
- **Verify:** An EF-version-only change yields `real_delta ≈ 0`, all method. A genuine spend/activity reduction yields real Δ. Deterministic.
- **Prompt:** *Read §1, §2. Create `progress/decompose.py`: diff two Epic A InventoryVersions using their lineage + EF-version metadata; attribute each category's change to real vs method/data. Assert the EF-only-change invariant.*

### E2 — Progress vs trajectory  (P.3.6.a)
- **Goal:** Compare real actuals to the Epic D trajectory; flag on/off-track; show hotspot movement.
- **Verify:** On-track when real reductions meet the trajectory; corporate hotspot year-over-year deltas surface.
- **Prompt:** *Read §3, §4. Create `progress/tracker.py` comparing the decomposed real total to the Epic D `targets` trajectory for the period; compute corporate hotspot movement. Persist a `target_progress` snapshot. Wire `POST /api/progress/track` + `GET /api/progress`.*

### E3 — Base-year recalculation  (P.3.6.b)
- **Goal:** Apply the GHG Protocol recalc policy above a significance threshold; enforce V2.0 single/physical base year.
- **Verify:** A >threshold M&A/method change recalculates the base year with recorded rationale; below-threshold does not. Single physical base year preserved.
- **Prompt:** *Read §1. Create `progress/recalc.py`: given a structural change + significance %, recalc the base-year InventoryVersion if above the configured threshold; record trigger + rationale in `base_year_recalcs`; keep a single physical base year (V2.0). Wire `POST /api/progress/recalc`.*

### E4 — Narrative + evals  (P.4.4.b)
- **Goal:** A grounded progress narrative; lock invariants.
- **Verify:** Narrative states real reductions only, cites the deltas, no fabricated numbers; `tests/test_progress.py` covers §7.
- **Prompt:** *Read §4, §7. Create `progress/narrative.py` (RAG-grounded, numbers from the decomposition). Wire `GET /api/progress/narrative`. Write `tests/test_progress.py`.*

---

## 7. New eval invariants

- A change driven solely by an EF-version/method change decomposes to ~0 real reduction (real vs method separation holds).
- Only real reductions count toward on/off-track status.
- Base-year recalculation occurs only above the significance threshold; each recalc records trigger + rationale.
- A single, physical (location-based) base year is preserved (V2.0).
- Progress narrative reports real reductions only and cites the underlying deltas; no fabricated numbers.

---

## 8. Risks & decisions

| Item | Type | Handling |
|---|---|---|
| Real-vs-method attribution accuracy | 🔴 credibility | Driven by Epic A lineage quality; the invariant guards the headline case. Prototype on two real successive inventories. |
| Significance threshold choice | 🟠 | Make configurable (data, not code); default to a GHG-Protocol-typical threshold, document it. |
| Depends on A + D | 🟠 | Needs versioned inventories and a target trajectory; sequence after both. |

---

## 9. Definition of done

An analyst re-runs their inventory a year later and the platform shows: **how much of the change was a real reduction vs. a method/data artifact**, whether they are **on or off their Epic D trajectory**, which categories moved, and — if a structural change crossed the threshold — a **recalculated base year with recorded rationale**, plus a **grounded progress narrative** that claims only real reductions. The tool is now the annual system of record.
