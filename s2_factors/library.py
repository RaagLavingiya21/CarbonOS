"""Grid emission-factor lookup (PRD 5.4). MVP stub.

Factors live in the `s2_factor_library` table (migration 032) and are seeded from
published datasets by scripts/seed_s2_factors.py. This module resolves a
(factor_type, region, reporting_period) request to a versioned factor row. The
lookup body is implemented in Phase M0; the interface is fixed here so s2_calc can
depend on it. Leaf module — imports nothing internal.
"""

from __future__ import annotations

from dataclasses import dataclass

FactorType = str  # egrid | iea | greene_residual | aib_residual | steam


@dataclass(frozen=True)
class EmissionFactor:
    factor_type: FactorType
    region_code: str
    vintage_year: int
    kg_co2e_per_mwh: float
    source_citation: str


def lookup_factor(
    factor_type: FactorType,
    region_code: str,
    reporting_year: int,
) -> EmissionFactor:
    """Resolve the factor in effect for a reporting year. Implemented in M0."""
    raise NotImplementedError(
        "s2_factors.library.lookup_factor is a Phase M0 deliverable; "
        "seed s2_factor_library and back this with s2_factor_store."
    )
