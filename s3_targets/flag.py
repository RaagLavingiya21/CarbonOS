"""FLAG (Forest, Land & Agriculture) target assessment (Epic D / P.3.3).

A company must set a separate SBTi FLAG target if it is in a FLAG-designated
sector (food, agriculture, forest products) OR if >=20% of its total emissions
come from FLAG activities. Pure logic, DB-free.

Sources: SBTi FLAG guidance; no-deforestation commitment date 31 Dec 2025
(FLAG V1.2) per research/reg-status-verified.md. The sector list is a dated
snapshot — treat as data to maintain, not eternal truth.
"""

from __future__ import annotations

from s3_targets.models import FlagAssessment

# FLAG-designated sector keywords (lower-case substring match on a sector label).
# Snapshot as of 2026-07-04 — maintain as SBTi guidance evolves.
_FLAG_SECTOR_KEYWORDS = (
    "food",
    "beverage",
    "agriculture",
    "agricultural",
    "farming",
    "dairy",
    "meat",
    "livestock",
    "crop",
    "forest",
    "forestry",
    "paper",
    "pulp",
    "timber",
    "tobacco",
    "textile",  # natural-fibre apparel supply chains often carry FLAG land emissions
)

_FLAG_SHARE_THRESHOLD = 0.20
_NO_DEFORESTATION_DATE = "2025-12-31"  # FLAG V1.2


def is_flag_sector(sector: str) -> bool:
    s = (sector or "").lower()
    return any(kw in s for kw in _FLAG_SECTOR_KEYWORDS)


def assess_flag(
    sector: str,
    total_kg_co2e: float,
    flag_kg_co2e: float = 0.0,
) -> FlagAssessment:
    """Determine whether a separate FLAG target is required.

    Args:
        sector: company sector label.
        total_kg_co2e: total emissions (all scopes or the relevant boundary).
        flag_kg_co2e: emissions attributable to FLAG activities (land/ag/forest).
    """
    share = (flag_kg_co2e / total_kg_co2e) if total_kg_co2e > 0 else 0.0
    by_sector = is_flag_sector(sector)
    by_share = share >= _FLAG_SHARE_THRESHOLD
    required = by_sector or by_share

    if required:
        reasons = []
        if by_sector:
            reasons.append(f"'{sector}' is a FLAG-designated sector")
        if by_share:
            reasons.append(f"FLAG emissions are {share:.0%} of total (>=20%)")
        reason = (
            "; ".join(reasons)
            + " — a separate FLAG target + no-deforestation commitment is required."
        )
    else:
        reason = "No FLAG target required (non-FLAG sector and FLAG emissions <20% of total)."

    return FlagAssessment(
        is_flag_required=required,
        flag_share=share,
        reason=reason,
        no_deforestation_commitment_date=_NO_DEFORESTATION_DATE if required else None,
    )
