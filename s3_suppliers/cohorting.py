"""Supplier cohorting (Epic F / P.3.4.a, P.2.3.a). Pure, DB-free.

Rank suppliers by their contribution (emissions or spend) and build a target
cohort from the hotspot categories — the fragmented-supply-base version of
"engage the ones that matter most first."
"""

from __future__ import annotations

from s3_suppliers.models import Supplier, SupplierCohort


def _key(basis: str):
    field = "emissions_kg" if basis == "emissions" else "spend_usd"
    return lambda s: getattr(s, field)


def rank_suppliers(suppliers: list[Supplier], basis: str = "emissions") -> list[Supplier]:
    """Suppliers sorted by descending contribution (ties broken by id for determinism)."""
    return sorted(suppliers, key=lambda s: (-_key(basis)(s), s.supplier_id))


def build_cohort(
    suppliers: list[Supplier],
    hotspot_categories: set[int],
    *,
    top_n: int = 20,
    basis: str = "emissions",
) -> SupplierCohort:
    """Top-N suppliers within the hotspot categories, ranked by contribution,
    with the share of those categories' emissions the cohort covers."""
    in_scope = [s for s in suppliers if s.scope3_category in hotspot_categories]
    ranked = rank_suppliers(in_scope, basis)
    members = ranked[:top_n]

    hotspot_total = sum(s.emissions_kg for s in in_scope)
    covered = sum(s.emissions_kg for s in members)
    pct = (covered / hotspot_total) if hotspot_total > 0 else 0.0

    return SupplierCohort(
        basis=basis,
        hotspot_categories=sorted(hotspot_categories),
        members=members,
        emissions_covered_pct=round(pct, 4),
    )
