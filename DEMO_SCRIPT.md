# Demo Script — 5-Minute Product Walkthrough

A guided script for showing the live product end-to-end — not the static `/demo` showcase page (which tells a pre-seeded water bottle story). Rehearse from this; don't read it verbatim.

**Before you start:** reset demo data to a clean state (once `scripts/seed_demo.py` exists, run it) and have `sample_boms/messy_tshirt.csv` ready to upload fresh, live — the messiness has to be real, not narrated.

---

## The BOM: `sample_boms/messy_tshirt.csv`

A cotton t-shirt BOM with real problems, on purpose:

| Row | Issue |
|---|---|
| `body` | Missing material |
| `thread` | Missing spend |
| `dye` — "reactive dye" | Expected low-confidence emission factor match |
| `Packaging` / `LDPE` (China) and `Packaging` / `LDPE` (India) | Near-duplicate rows — same component, material, spend, and supplier; only country differs |

Four distinct flag types in one small file — enough to demonstrate the parser without the walkthrough dragging.

---

## The Walkthrough

### 1. Upload → flags surface live — ✅ live today
Upload the CSV. Say: *"Nothing here gets silently guessed — anything questionable gets surfaced to the analyst."* Point out as they appear: the missing material, the missing spend, and the flagged duplicate packaging rows.

### 2. Review flags, see matched factors — ✅ live today
Walk through the emission-factor matches: confidence scores per row, source citation (Open CEDA 2025), and the low-confidence flag on "reactive dye" with suggested alternatives. Say: *"Every number traces back to a source — this is what makes it audit-ready, not just a spreadsheet formula."*

### 3. Calculate → footprint + hotspots — ✅ live today
Show the total kg CO₂e, the hotspot ranking, and the critic's validation (total equals the sum of line items, flagged automatically if not). Say: *"This is deterministic and checked — not an LLM guessing the math."*

### 4. Approve → Export PACT payload — ✅ live today (Phase 1)
Approve the analysis, click **Export PACT payload**, show the JSON. Say: *"This isn't a proprietary export — it validates against the WBCSD PACT v3 schema, the actual standard enterprise supply chains use to exchange footprint data."*

### 5. Dashboard drill-down — 🔜 pending Phase 2
KPI card on the dashboard → click into the filtered product list → click into this footprint → click into the line item → land on the EF source citation. Say: *"Every aggregate number is a link to the records that produced it — nothing is a dead end."*

### 6. Supplier response raises PDS — 🔜 pending Phase 3
Route an incoming supplier reply → watch the footprint recalculate, version bump, and Primary Data Share rise from a screening-grade 0% toward something real. Say: *"This is the loop that turns an industry-average estimate into your actual supply chain."*

### 7. Scenario comparison — 🔜 pending Phase 4
Duplicate the baseline, swap the highest-hotspot material for a lower-carbon alternative, show the side-by-side delta. Say: *"Now it's not just measurement — it's a decision-making tool."*

---

## The one-sentence pitch

*"It turns a messy spreadsheet into an auditable, standards-aligned product carbon footprint that an analyst can trust, manage, improve, and share — with AI doing the tedious parts, not the judgment calls."*

---

**Keep this file honest.** Update the ✅/🔜 tags the moment a phase merges — never perform a beat marked 🔜 as if it's real.
