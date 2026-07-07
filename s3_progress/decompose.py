"""Δ decomposition: real reductions vs method/data-driven changes (Epic E / E1).

The credibility of any progress claim rests on this split (plan §1): a category's
change counts as a REAL reduction only when it is like-for-like — same
calculation method and same emission-factor version. If the method changed
(spend→activity), the EF library version changed, or the category is newly
measured/dropped (completeness), the change is method-driven and must NOT be
reported as a real reduction.

Pure logic, deterministic, DB-free.
"""

from __future__ import annotations

from s3_progress.models import (
    CategoryDelta,
    Decomposition,
    InventorySnapshot,
)


def decompose(base: InventorySnapshot, current: InventorySnapshot) -> Decomposition:
    """Split the base→current change into real vs method deltas, per category."""
    base_map = base.by_category
    cur_map = current.by_category
    deltas: list[CategoryDelta] = []

    for cat in sorted(set(base_map) | set(cur_map)):
        b = base_map.get(cat)
        c = cur_map.get(cat)

        if b is not None and c is not None:
            total = c.kg_co2e - b.kg_co2e
            if b.method != c.method:
                deltas.append(_method(cat, b.kg_co2e, c.kg_co2e, total, "method_change"))
            elif b.ef_version != c.ef_version:
                deltas.append(_method(cat, b.kg_co2e, c.kg_co2e, total, "ef_version_change"))
            else:
                deltas.append(CategoryDelta(cat, b.kg_co2e, c.kg_co2e, total, total, 0.0, "real"))
        elif c is not None:  # newly measured category → completeness (method), not a real rise
            deltas.append(_method(cat, 0.0, c.kg_co2e, c.kg_co2e, "new_category"))
        else:  # dropped from scope → method, not a real cut
            deltas.append(_method(cat, b.kg_co2e, 0.0, -b.kg_co2e, "dropped_category"))

    return Decomposition(
        base_year=base.reporting_year,
        current_year=current.reporting_year,
        category_deltas=deltas,
    )


def _method(cat: int, base_kg: float, cur_kg: float, total: float, reason: str) -> CategoryDelta:
    return CategoryDelta(
        scope3_category=cat,
        base_kg=base_kg,
        current_kg=cur_kg,
        total_delta=total,
        real_delta=0.0,
        method_delta=total,
        reason=reason,
    )
