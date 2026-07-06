"""Emission-factor library + selection hierarchy.

The library holds a set of EmissionFactor rows and resolves the applicable one
for a (fuel, category, gas) request. In production it is built from the
`s1_ef_record` DB rows; in tests / headless runs it defaults to the canonical
EPA set. Selection follows the research/2.1 hierarchy: the lowest selection_rank
wins (measured < supplier < national < regional < IPCC). For model-year-specific
mobile factors, the exact year is preferred, else the nearest not-newer year.
"""

from __future__ import annotations

from s1_factors.epa_library import EPA_FACTORS
from s1_factors.models import EmissionFactor, MissingEmissionFactor


class EmissionFactorLibrary:
    def __init__(self, factors: list[EmissionFactor]) -> None:
        self._factors = list(factors)

    @classmethod
    def default(cls) -> EmissionFactorLibrary:
        """The canonical EPA-anchored library (no DB required)."""
        return cls(EPA_FACTORS)

    @classmethod
    def from_db_rows(cls, rows: list[dict]) -> EmissionFactorLibrary:
        """Build from s1_ef_record rows (only active rows: valid_to IS NULL)."""
        factors = [
            EmissionFactor(
                fuel_or_activity=r["fuel_or_activity"],
                source_category=r["source_category"],
                gas=r["gas"],
                value=float(r["value"]),
                unit=r["unit"],
                source=r["source"],
                source_version=r["source_version"],
                region=r.get("region", "US"),
                tier=r.get("tier") or 1,
                biogenic=bool(r.get("biogenic", False)),
                model_year=r.get("model_year"),
                hhv=float(r["hhv"]) if r.get("hhv") is not None else None,
                hhv_unit=r.get("hhv_unit"),
            )
            for r in rows
            if r.get("valid_to") is None
        ]
        return cls(factors)

    def select(
        self,
        fuel_or_activity: str,
        source_category: str,
        gas: str,
        *,
        region: str = "US",
        model_year: int | None = None,
    ) -> EmissionFactor:
        """Return the applicable EF, or raise MissingEmissionFactor."""
        candidates = [
            f for f in self._factors
            if f.fuel_or_activity == fuel_or_activity
            and f.source_category == source_category
            and f.gas == gas
            and f.region == region
        ]
        if not candidates:
            raise MissingEmissionFactor(
                f"No EF for fuel={fuel_or_activity} category={source_category} "
                f"gas={gas} region={region}"
            )

        if model_year is not None and any(c.model_year is not None for c in candidates):
            candidates = _resolve_model_year(candidates, model_year)

        # Lowest selection_rank wins; ties resolved deterministically by source.
        return min(candidates, key=lambda f: (f.selection_rank, f.source))


def _resolve_model_year(
    candidates: list[EmissionFactor], model_year: int
) -> list[EmissionFactor]:
    """Prefer the exact model year, else the nearest not-newer, else the nearest."""
    exact = [c for c in candidates if c.model_year == model_year]
    if exact:
        return exact
    not_newer = [c for c in candidates if c.model_year is not None and c.model_year <= model_year]
    pool = not_newer or [c for c in candidates if c.model_year is not None]
    nearest = min(pool, key=lambda c: abs((c.model_year or 0) - model_year))
    return [c for c in pool if c.model_year == nearest.model_year]
