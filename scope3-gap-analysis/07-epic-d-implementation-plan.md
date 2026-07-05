# Implementation Plan — Epic D: SBTi + FLAG Target-Setting

**Branch:** `feature/scope3-mvp`
**Status:** Plan, pre-implementation
**Source:** `03-enhancement-roadmap.md` Epic D; `00-program-overview.md` §2. Depends on **Epic A** (inventory = coverage denominator) and reuses **Epic C** `obligations/sbti_readiness.py` (Category A/B + coverage math).

> **What this epic is.** The research's **JTBD-4: "set targets that will be accepted."** A guided, standards-conformant SBTi target wizard — near-term and net-zero coverage math done for the analyst — plus the FLAG module for food/ag brands, and a validation-submission pack. Turns a measured inventory into a validatable commitment.

> **What this epic is NOT.** Not the *readiness/trigger* diagnosis (that's Epic C — "are you obligated, are you Category A/B"). Epic D assumes the company knows it must set a target and helps it *build one that passes*. Not progress tracking (Epic E). Not a decarbonization plan (levers are Epic I).

Research units closed: **P.3.2.a/.b/.c** (SBTi target wizard — coverage math, absolute vs intensity, version-aware), **P.3.3.a/.b** (FLAG target + no-deforestation), **P.4.4.a** (SBTi validation packaging).

---

## 1. The version + honesty constraint (read first)

SBTi is mid-transition and partly unconfirmed; the wizard must be **version-aware and honest**, enforced as invariants (per `research/reg-status-verified.md` §5):

1. **Encode both regimes, default correctly.** V1.x (≥40% trigger, 67% near-term / 90% net-zero aggregate) **and** V2.0 (per-category ≥5% coverage, Category A/B, physical + single base year, base-year limited assurance for Cat A). **Default to V2.0 for targets landing 2027+**; offer V1.3.1 only inside the transition window (submissions accepted until 31 Jan 2028).
2. **Do not hardcode the V2.0 net-zero coverage %.** The near-term per-category ≥5% rule is confirmed; the net-zero long-term % is described as "near-total" but not cleanly confirmed. Return it as `unconfirmed`, cite the need to verify against the V2.0 standard text — never a fabricated number.
3. **Enforce V2.0 base-year rules structurally.** Physical (location-based) inventory; **single base year across all scopes**. The wizard refuses to build a V2.0 target on a market-based or multi-base-year inventory and flags the requirement.
4. **Numbers looked up, not generated** (shared discipline): coverage %, base-year totals, and reduction math come from the Epic A inventory; the LLM only phrases guidance.

---

## 2. What the wizard computes (from the inventory)

| Input | Source | Used for |
|---|---|---|
| Category A/B classification | Epic C `sbti_readiness` (revenue >$1B OR >500 emp → A) | Is Scope 3 mandatory? Is base-year assurance required? |
| Per-category Scope 3 totals + % of total | Epic A `inventory_category_results` | V2.0 per-category ≥5% coverage set; V1.x 67%/90% aggregate |
| FLAG share of total emissions | Epic A Cat-1 materials/sector tags | FLAG target required if FLAG sector OR ≥20% of total from FLAG |
| Base year (physical, single) | Epic A `inventory_versions` (base flag) | Absolute-contraction / intensity trajectory anchor |

**ICP note:** a mid-market consumer brand is almost always Category A → Scope 3 target mandatory + base-year limited assurance, and the ≥5%-per-category rule typically pulls in Cat 1 plus Cat 4/9/11/12 — so more categories must be target-covered than under the old 67% shortcut. The wizard surfaces exactly which categories need coverage.

---

## 3. New data model (migrations `040`–`042`)

| Table | Purpose | Key columns |
|---|---|---|
| `targets` | A target (near-term or net-zero) | `target_id`, `org_id`, `type` (`near_term`/`net_zero`), `method` (`absolute`/`intensity`), `sbti_version`, `base_year`, `target_year`, `reduction_pct`, `inventory_base_id`, `status` (`draft`/`ready`/`validated`), `assurance_required` |
| `target_categories` | Per-category coverage for a target | `target_id`, `category_num`, `pct_of_scope3`, `is_covered`, `requires_coverage` (≥5% flag) |
| `flag_targets` | FLAG-specific target + no-deforestation | `target_id`, `flag_share_pct`, `flag_target_type`, `no_deforestation_commitment_date` |

The `Target` entity was stubbed in Epic A's shared data model; Epic D fills it in.

---

## 4. New modules (business logic — no UI imports)

| Module | Responsibility | Reuses |
|---|---|---|
| `targets/sbti_wizard.py` | Version-aware coverage math + trajectory (absolute vs intensity); build a conformant draft target | **Epic C `obligations/sbti_readiness.py`** (Cat A/B + ≥5% math — do not duplicate); Epic A inventory |
| `targets/flag.py` | FLAG designation (sector or ≥20%); no-deforestation commitment; separate FLAG target | Epic A Cat-1 material/sector tags |
| `targets/validation_pack.py` | Assemble the SBTi validation submission (P.4.4.a) | `audit_log`/citations lineage; methodology metadata |
| `db/target_store.py` | CRUD for the 3 tables | `db/store.py`, `db/inventory_store.py` |

---

## 5. API routes (`api/routes/targets.py` — orchestrate only)

| Endpoint | Method | Does |
|---|---|---|
| `/api/targets/wizard` | POST | Given `inventory_id` + horizon + method → computed coverage requirements + draft target |
| `/api/targets` | POST/GET | Save / list targets |
| `/api/targets/{id}/flag` | POST | Attach a FLAG target + no-deforestation date |
| `/api/targets/{id}/validation-pack` | POST | Assemble the SBTi validation submission |

---

## 6. Sub-phases

### D1 — Target data model & store
- **Goal:** 3 tables + CRUD; fill in the Epic A `Target` stub.
- **Verify:** Branch DB; create/read a target org-scoped; RLS enforced.
- **Prompt:** *Read §3. Create migrations 040–042 (RLS org-scoped like `027`). Add `db/target_store.py`. No target math yet.*

### D2 — SBTi coverage math + wizard  ⭐ version-critical  (P.3.2.a/.b/.c)
- **Goal:** Compute version-aware coverage requirements and a draft trajectory from an inventory.
- **Verify:** V2.0 → every category ≥5% flagged `requires_coverage`, computed from `inventory_category_results`. V1.x → 67%/90% aggregate. Net-zero % returns `unconfirmed`. Absolute-contraction default; intensity optional. Category A → assurance flagged. Refuses market-based / multi-base-year inventory for V2.0.
- **Prompt:** *Read §1, §2, §3 and `reg-status-verified.md` §5. Create `targets/sbti_wizard.py`. Call Epic C `sbti_readiness` for Cat A/B + the ≥5% denominator — do not reimplement. Compute the covered/required category set and an absolute (default) or intensity trajectory. Return net-zero coverage % as `unconfirmed`. Enforce §1.3 base-year rules. Wire `POST /api/targets/wizard`.*

### D3 — FLAG module  (P.3.3.a/.b)
- **Goal:** Determine FLAG applicability and build a separate FLAG target with a no-deforestation commitment.
- **Verify:** FLAG required when sector is FLAG-designated OR FLAG ≥20% of total (from Cat-1 tags). Separate FLAG target created; no-deforestation date captured (default 31 Dec 2025 per FLAG V1.2).
- **Prompt:** *Read §2 (FLAG row). Create `targets/flag.py`: compute FLAG share from Epic A Cat-1 material/sector tags; if FLAG-sector or ≥20%, require a separate FLAG target + no-deforestation commitment. Wire `POST /api/targets/{id}/flag`.*

### D4 — Validation pack  (P.4.4.a)
- **Goal:** Assemble the SBTi submission package.
- **Verify:** Pack includes target definitions, coverage math, base-year inventory reference, assurance note (Cat A), methodology + lineage. Numbers trace to the inventory.
- **Prompt:** *Read §4. Create `targets/validation_pack.py` assembling the SBTi validation submission from the target + Epic A inventory + lineage/citations. Wire `POST /api/targets/{id}/validation-pack`.*

### D5 — Evals
- **Prompt:** *Write `tests/test_targets.py` asserting every §7 invariant.*

---

## 7. New eval invariants

- V2.0 per-category ≥5% coverage set is computed correctly from the inventory; V1.x uses 67%/90% aggregate.
- Net-zero coverage % is reported `unconfirmed` — never hardcoded.
- V2.0 targets require a physical, single-base-year inventory; the wizard refuses otherwise.
- Category A → Scope 3 target present + base-year limited assurance flagged.
- FLAG target created iff FLAG sector or FLAG ≥20% of total; no-deforestation date present.
- Absolute-contraction is the default method; coverage/reduction numbers trace to the inventory (none LLM-generated).

---

## 8. Risks & decisions

| Item | Type | Handling |
|---|---|---|
| SBTi version transition | 🟠 | Version-aware; default V2.0 for 2027+; V1.3.1 only in the transition window. |
| Net-zero % unconfirmed | 🔴 credibility | Return `unconfirmed` (invariant); verify against V2.0 standard text before ever hardcoding. |
| Dependency on Epic A | 🟠 | Needs per-category totals + a physical single-base-year inventory. Sequence after A. |
| FLAG sector list currency | 🟠 | Maintain the FLAG-designated sector list as data (same discipline as the obligation ruleset). |

---

## 9. Definition of done

An analyst with a locked Epic A inventory runs the wizard and gets: their **Category A/B status**, the **exact set of Scope 3 categories that need target coverage** (V2.0 ≥5% each), an **absolute or intensity trajectory** to a chosen target year, a **FLAG target** if their materials trigger it, and a **validation pack** ready for SBTi — with every number traced to the inventory, the net-zero figure honestly marked unconfirmed, and V2.0 base-year rules enforced.
