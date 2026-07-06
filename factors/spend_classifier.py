"""Spend → Scope 3 category classifier (Epic A / unit P.2.2.b).

Given a normalized GL/ERP spend line, decide:
  1. which Scope 3 category (1–15) it belongs to, and
  2. its Open CEDA 2025 EEIO sector + emission factor (kg CO2e per USD).

Design (see scope3-gap-analysis/04-epic-a-implementation-plan.md §3):
  - The *sector → EF* half is delegated wholesale to `factors/ef_lookup.py`,
    which already does fuzzy `text → CEDA sector → EF` matching with a
    confidence score and analyst-override support. We do not reimplement it.
  - The *net-new* half is the `GL line → Scope 3 category` decision. GL lines
    are dominated by services/transport/energy/capital terms that the
    BOM-material-oriented fuzzy matcher handles poorly, so we add a small,
    auditable GL-term lexicon that maps common terms directly to a CEDA sector
    code + Scope 3 category. Anything the lexicon misses falls back to
    `lookup_ef` for the sector, then to a sector → category mapping.

Everything here is deterministic (no LLM, no network): the same spend line
always yields the same classification, satisfying the Epic A determinism
invariant and letting the eval run in CI without API keys.

Scope note (honesty): spend-based screening naturally covers Cat 1, 2, 3, 4,
5, 6. Direct fuel combustion is Scope 1 and purchased electricity is Scope 2 —
only their *upstream* (well-to-tank / T&D) portion is Scope 3 Cat 3. Energy/fuel
lines are therefore classified Cat 3 but flagged `review_scope` so an analyst
confirms the Scope 1/2 split. Cat 7–15 generally need activity/product data
(Epic H), not spend, and are not asserted here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from factors.ef_lookup import (
    CONFIDENCE_MATCH,
    EFMatch,
    lookup_ef,
    lookup_ef_by_sector_code,
)

# --- Scope 3 category catalogue (GHG Protocol Corporate Value Chain Std) -----

SCOPE3_CATEGORY_NAMES: dict[int, str] = {
    1: "Purchased goods and services",
    2: "Capital goods",
    3: "Fuel- and energy-related activities (not in Scope 1 or 2)",
    4: "Upstream transportation and distribution",
    5: "Waste generated in operations",
    6: "Business travel",
    7: "Employee commuting",
    8: "Upstream leased assets",
    9: "Downstream transportation and distribution",
    10: "Processing of sold products",
    11: "Use of sold products",
    12: "End-of-life treatment of sold products",
    13: "Downstream leased assets",
    14: "Franchises",
    15: "Investments",
}

# CEDA sector codes grouped by the Scope 3 category they most cleanly map to.
# Used by the sector → category fallback (when the GL lexicon does not fire).
_SECTOR_CAT4_FREIGHT = {"482000", "483000", "484000", "486000", "492000", "493000"}
_SECTOR_CAT6_TRAVEL = {"481000", "485000", "48A000", "561500", "721000"}
_SECTOR_CAT5_WASTE = {"562000"}
_SECTOR_CAT3_ENERGY = {"211000", "221100", "221200", "324110"}


@dataclass
class SpendClassification:
    """Classifier output for one spend line (mirrors the `spend_classifications`
    table columns in Epic A §2)."""

    description: str
    scope3_category: int
    scope3_category_name: str
    eeio_sector_code: str
    eeio_sector_name: str
    ef_kg_co2e_per_usd: float
    confidence_score: float
    data_source: str = "spend"
    kg_co2e: float | None = None  # amount_usd × ef, when amount provided
    flag_status: str = "ok"  # ok | low_confidence | no_match | review_scope
    ef_source: str = ""
    rationale: str = ""
    suggested_alternatives: list[str] = field(default_factory=list)


# --- GL-term lexicon --------------------------------------------------------
# Ordered, most-specific first. Each rule: (compiled pattern, sector_code,
# scope3_category, human rationale). Curated, so matches are high-confidence.
# Patterns are matched against the lower-cased "description + vendor" text.

_LexRule = tuple[re.Pattern[str], str, int, str]


def _rule(pattern: str, sector_code: str, category: int, why: str) -> _LexRule:
    return (re.compile(pattern, re.I), sector_code, category, why)


_GL_LEXICON: list[_LexRule] = [
    # --- Cat 6 business travel (check before generic transport) ---
    _rule(r"\bair\s*travel|airfare|airline|flight\b", "481000", 6, "air travel term"),
    _rule(r"\bhotel|lodging|accommodation\b", "721000", 6, "accommodation term"),
    _rule(
        r"\btravel (booking|arrangement|agency|reservation)|per\s?diem\b",
        "561500",
        6,
        "travel-booking term",
    ),
    _rule(r"\brental car|car rental|rideshare|taxi\b", "485000", 6, "ground passenger travel term"),
    # --- Cat 4 upstream transport & distribution ---
    _rule(r"\b(freight|trucking|truckload|ltl|drayage)\b", "484000", 4, "trucking/freight term"),
    _rule(
        r"\bocean freight|sea freight|container ship|maritime shipping\b",
        "483000",
        4,
        "ocean freight term",
    ),
    _rule(r"\brail freight|rail transport|railway\b", "482000", 4, "rail freight term"),
    _rule(r"\bwarehous|storage services|fulfillment center\b", "493000", 4, "warehousing term"),
    _rule(
        r"\bcourier|parcel|last[- ]mile|inbound logistics|3pl\b",
        "492000",
        4,
        "courier/logistics term",
    ),
    _rule(r"\bpipeline\b", "486000", 4, "pipeline transport term"),
    # --- Cat 5 waste ---
    _rule(
        r"\bwaste (hauling|disposal|management|removal)"
        r"|hazardous waste|recycling services|landfill\b",
        "562000",
        5,
        "waste-service term",
    ),
    # --- Cat 3 fuel & energy (flagged for Scope 1/2 review) ---
    _rule(r"\bnatural gas\b", "221200", 3, "natural gas supply term"),
    _rule(
        r"\b(diesel|gasoline|petrol|jet fuel|fuel oil|propane)\b",
        "324110",
        3,
        "purchased fuel term",
    ),
    _rule(
        r"\belectricity|electric power|kwh|utility power\b",
        "221100",
        3,
        "purchased electricity term",
    ),
    # --- Cat 2 capital goods (durable equipment, by GL intent) ---
    _rule(
        r"\b(laptop|desktop|server|workstation|computer)s?\b", "334111", 2, "IT hardware (capital)"
    ),
    _rule(
        r"\b(machinery|cnc|industrial equipment|manufacturing equipment|production line)\b",
        "333120",
        2,
        "machinery (capital)",
    ),
    _rule(
        r"\b(furniture|desks?|chairs?|shelving|fixtures)\b",
        "337900",
        2,
        "furniture & fixtures (capital)",
    ),
    _rule(
        r"\b(vehicle|van|truck) (fleet|purchase)|forklift\b", "423100", 2, "vehicle/fleet (capital)"
    ),
]

# Sector codes referenced by the lexicon must exist in CEDA; if a code is not
# present the rule degrades gracefully to the fuzzy path (see _from_sector_code).


def _clean(text: str) -> str:
    """Collapse whitespace; keep it simple and deterministic."""
    return re.sub(r"\s+", " ", text or "").strip()


def _sector_to_scope3_category(sector_code: str, sector_name: str) -> tuple[int, str]:
    """Map a resolved CEDA sector to a Scope 3 category (fallback path).

    Returns (category, rationale). Defaults to Cat 1 (purchased goods/services).
    """
    name = sector_name.lower()
    if sector_code in _SECTOR_CAT4_FREIGHT:
        return 4, f"CEDA sector {sector_code} is upstream transport"
    if sector_code in _SECTOR_CAT6_TRAVEL:
        return 6, f"CEDA sector {sector_code} is travel/accommodation"
    if sector_code in _SECTOR_CAT5_WASTE:
        return 5, f"CEDA sector {sector_code} is waste services"
    if sector_code in _SECTOR_CAT3_ENERGY or re.search(
        r"petroleum|natural gas|electric power|fuel", name
    ):
        return 3, f"CEDA sector {sector_code} is fuel/energy"
    return 1, "default: purchased goods & services"


def _finalize(
    description: str,
    ef: EFMatch,
    category: int,
    rationale: str,
    amount_usd: float | None,
    *,
    force_flag: str | None = None,
) -> SpendClassification:
    """Assemble a SpendClassification from an EFMatch + a chosen category."""
    if ef.is_no_match:
        flag = "no_match"
    elif ef.is_low_confidence:
        flag = "low_confidence"
    else:
        flag = "ok"
    # Energy/fuel lines: even a confident match needs a Scope 1/2 sanity check.
    if force_flag and flag == "ok":
        flag = force_flag

    kg = round(amount_usd * ef.ef_kg_co2e_per_usd, 6) if amount_usd is not None else None

    return SpendClassification(
        description=description,
        scope3_category=category,
        scope3_category_name=SCOPE3_CATEGORY_NAMES[category],
        eeio_sector_code=ef.sector_code,
        eeio_sector_name=ef.sector_name,
        ef_kg_co2e_per_usd=ef.ef_kg_co2e_per_usd,
        confidence_score=ef.confidence_score,
        kg_co2e=kg,
        flag_status=flag,
        ef_source=ef.source_citation,
        rationale=rationale,
        suggested_alternatives=list(ef.suggested_alternatives),
    )


def classify_spend_line(
    description: str,
    *,
    vendor: str | None = None,
    amount_usd: float | None = None,
    country: str | None = None,
    overrides: dict[str, str] | None = None,
) -> SpendClassification:
    """Classify one GL/ERP spend line into a Scope 3 category + CEDA EF.

    Args:
        description: GL line description (the primary signal).
        vendor:      Optional vendor/supplier name (added to the match text).
        amount_usd:  Optional spend amount → populates kg_co2e.
        country:     Optional country for country-specific EF selection.
        overrides:   Optional {normalized_text: sector_code} analyst overrides,
                     forwarded to ef_lookup (override → confidence 100).

    Returns:
        SpendClassification. Low-confidence / unmatched lines are flagged for
        human review; energy/fuel lines are flagged `review_scope`.
    """
    text = _clean(f"{description} {vendor or ''}")

    # 1. Analyst override wins outright (delegated to ef_lookup override path).
    if overrides:
        ef = lookup_ef(text, country, overrides=overrides)
        if not ef.is_no_match and ef.confidence_score >= CONFIDENCE_MATCH:
            category, why = _sector_to_scope3_category(ef.sector_code, ef.sector_name)
            return _finalize(description, ef, category, f"analyst override → {why}", amount_usd)

    # 2. GL-term lexicon (curated, high-confidence, GL-oriented).
    for pattern, sector_code, category, why in _GL_LEXICON:
        if pattern.search(text):
            try:
                ef = lookup_ef_by_sector_code(sector_code, country)
            except ValueError:
                continue  # sector code absent from this CEDA build → fall through
            force = "review_scope" if category == 3 else None
            return _finalize(
                description, ef, category, f"GL lexicon: {why}", amount_usd, force_flag=force
            )

    # 3. Fuzzy fallback: let ef_lookup resolve the sector, then map to category.
    ef = lookup_ef(text, country)
    if ef.is_no_match:
        return _finalize(description, ef, 1, "no sector match — needs human review", amount_usd)

    category, why = _sector_to_scope3_category(ef.sector_code, ef.sector_name)
    force = "review_scope" if category == 3 else None
    return _finalize(
        description, ef, category, f"fuzzy match → {why}", amount_usd, force_flag=force
    )
