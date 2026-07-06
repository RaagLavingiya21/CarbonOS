"""Grid emission-factor library with vintage pinning (PRD 5.4).

Factors are stored per vintage year. A reporting period resolves to the factor
whose vintage is the latest one **at or before** the reporting year, so a reporting
period always uses the factor set in effect for it and an annual refresh (adding a
newer vintage) never silently restates a historical period.

Pure business logic — the persistence layer (s2_factor_store, migration 042) hands
this module a plain list of EmissionFactor rows; it imports nothing internal.
"""

from __future__ import annotations

from dataclasses import dataclass

# Factor families. Location-based uses grid-average (egrid/iea); market-based uses
# residual mix for uncovered load, or a supplier-specific/green-tariff factor.
FactorType = str  # egrid | iea | greene_residual | aib_residual | steam


@dataclass(frozen=True)
class EmissionFactor:
    factor_type: FactorType
    region_code: str
    vintage_year: int
    kg_co2e_per_mwh: float
    source_citation: str


class FactorNotFoundError(LookupError):
    """No factor matches the requested type/region at or before the reporting year."""


class FactorLibrary:
    """In-memory view over a set of versioned emission factors."""

    def __init__(self, factors: list[EmissionFactor]) -> None:
        self._factors = list(factors)

    def resolve(
        self,
        factor_type: FactorType,
        region_code: str,
        reporting_year: int,
    ) -> EmissionFactor:
        """Return the factor for (type, region) pinned to `reporting_year`.

        Picks the candidate with the greatest vintage_year that does not exceed
        the reporting year. Raises FactorNotFoundError if none qualifies.
        """
        candidates = [
            f
            for f in self._factors
            if f.factor_type == factor_type
            and f.region_code == region_code
            and f.vintage_year <= reporting_year
        ]
        if not candidates:
            raise FactorNotFoundError(
                f"No '{factor_type}' factor for region '{region_code}' "
                f"with vintage <= {reporting_year}."
            )
        return max(candidates, key=lambda f: f.vintage_year)
