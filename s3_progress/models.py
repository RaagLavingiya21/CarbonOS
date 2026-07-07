"""Dataclasses for Scope-3 progress tracking + base-year recalc (Epic E).

DB-free. The API layer maps corporate InventoryVersions (Epic A) onto
InventorySnapshot; the math here is pure and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CategoryPoint:
    scope3_category: int
    kg_co2e: float
    method: str = "spend"  # spend | product_rollup | activity
    ef_version: str = "CEDA-2025"  # emission-factor library version


@dataclass
class InventorySnapshot:
    reporting_year: int
    categories: list[CategoryPoint] = field(default_factory=list)

    @property
    def total_kg_co2e(self) -> float:
        return sum(c.kg_co2e for c in self.categories)

    @property
    def by_category(self) -> dict[int, CategoryPoint]:
        return {c.scope3_category: c for c in self.categories}


@dataclass
class CategoryDelta:
    scope3_category: int
    base_kg: float
    current_kg: float
    total_delta: float  # current - base (negative = reduction)
    real_delta: float  # like-for-like change (same method + EF version)
    method_delta: float  # change attributable to method/EF/completeness change
    reason: str  # real | method_change | ef_version_change | new_category | dropped_category


@dataclass
class Decomposition:
    base_year: int
    current_year: int
    category_deltas: list[CategoryDelta] = field(default_factory=list)

    @property
    def total_delta(self) -> float:
        return sum(d.total_delta for d in self.category_deltas)

    @property
    def real_delta(self) -> float:
        return sum(d.real_delta for d in self.category_deltas)

    @property
    def method_delta(self) -> float:
        return sum(d.method_delta for d in self.category_deltas)


@dataclass
class ProgressResult:
    current_year: int
    base_total_kg: float
    real_total_kg: float  # base + real change only (like-for-like)
    actual_total_kg: float  # the raw current total (incl. method changes)
    trajectory_target_kg: float | None
    on_track: bool | None  # None when no trajectory target for the year
    method_delta_kg: float  # portion of the change that is NOT a real reduction
    notes: list[str] = field(default_factory=list)


@dataclass
class RecalcDecision:
    trigger: str  # ma | divestment | methodology | structural | error_correction
    significance_pct: float
    threshold_pct: float
    recalc_required: bool
    rationale: str
