"""Corporate 15-category Scope 3 inventory aggregation (Epic A / unit P.2.2.c + A4).

Pure logic (no DB/UI): takes a parsed GL spend file, classifies each usable line
via factors/spend_classifier.py, and rolls the results up into per-category
totals and a single corporate number.

Two reconciliation rules from 04-epic-a-implementation-plan.md §1:
  - "Screen then deepen": spend-based gives a fast, complete first pass; where
    richer data exists it REPLACES the spend estimate for that category.
  - Cat 1 therefore comes from the product-PCF rollup (calc/rollup.py) when
    products exist, else from spend — NEVER both (no double-count). The product
    Cat-1 total is injected here as `product_cat1_kg` so this module stays
    DB-free and unit-testable; the API layer supplies it from db/rollup_store.

Invariants asserted (extending the CLAUDE.md "every number traceable" rules to
corporate altitude):
  - corporate total == sum of category totals
  - a spend-method category total == sum of its line contributions
  - kg_co2e == amount_usd × ef for every classified line (guaranteed upstream
    by the classifier; re-checked here)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from factors.spend_classifier import (
    SCOPE3_CATEGORY_NAMES,
    SpendClassification,
    classify_spend_line,
)
from parsing.spend_parser import ParsedSpend, SpendLine


@dataclass
class CategoryResult:
    scope3_category: int
    category_name: str
    total_kg_co2e: float
    line_count: int
    method: str  # "spend" | "product_rollup"
    low_confidence_count: int = 0
    review_scope_count: int = 0  # energy/fuel lines needing Scope 1/2 review
    classifications: list[SpendClassification] = field(default_factory=list)


@dataclass
class InventoryResult:
    category_results: list[CategoryResult]
    total_kg_co2e: float
    classified_line_count: int
    excluded_line_count: int
    excluded_reasons: dict[str, int]  # reason -> count

    @property
    def category_totals(self) -> dict[int, float]:
        return {c.scope3_category: c.total_kg_co2e for c in self.category_results}

    @property
    def hotspots(self) -> list[CategoryResult]:
        """Categories sorted descending by total (the corporate hotspots)."""
        return sorted(self.category_results, key=lambda c: c.total_kg_co2e, reverse=True)


def _usable(line: SpendLine) -> tuple[bool, str | None]:
    """A line is usable for the inventory when it has a description (to classify)
    and a positive amount (credits/zeros/missing are excluded, with a reason)."""
    if line.description is None:
        return False, "missing_description"
    if line.amount_usd is None:
        return False, "missing_amount"
    if line.amount_usd <= 0:
        return False, "credit_or_zero"
    return True, None


def build_inventory_from_spend(
    parsed_spend: ParsedSpend,
    *,
    country: str | None = None,
    product_cat1_kg: float | None = None,
) -> InventoryResult:
    """Classify + aggregate a parsed GL file into a 15-category inventory.

    Args:
        parsed_spend: output of parsing.spend_parser.parse_spend_csv.
        country: optional country for country-specific EFs.
        product_cat1_kg: if provided, the product-PCF rollup total for Cat 1;
            replaces the spend-based Cat 1 estimate (method -> product_rollup).

    Returns an InventoryResult (per-category totals + corporate total).
    """
    buckets: dict[int, list[SpendClassification]] = {}
    excluded_reasons: dict[str, int] = {}
    classified = 0

    for line in parsed_spend.rows:
        ok, reason = _usable(line)
        if not ok:
            excluded_reasons[reason] = excluded_reasons.get(reason, 0) + 1
            continue
        clf = classify_spend_line(
            line.description,  # type: ignore[arg-type]  (usable => not None)
            vendor=line.vendor,
            amount_usd=line.amount_usd,
            country=country,
        )
        if clf.flag_status == "no_match" or clf.kg_co2e is None:
            excluded_reasons["no_ef_match"] = excluded_reasons.get("no_ef_match", 0) + 1
            continue
        buckets.setdefault(clf.scope3_category, []).append(clf)
        classified += 1

    category_results = _aggregate(buckets, product_cat1_kg)

    total = sum(c.total_kg_co2e for c in category_results)
    # Invariant: corporate total == sum of category totals.
    assert math.isclose(total, sum(c.total_kg_co2e for c in category_results), rel_tol=1e-9)

    return InventoryResult(
        category_results=sorted(category_results, key=lambda c: c.scope3_category),
        total_kg_co2e=total,
        classified_line_count=classified,
        excluded_line_count=sum(excluded_reasons.values()),
        excluded_reasons=excluded_reasons,
    )


def _aggregate(
    buckets: dict[int, list[SpendClassification]],
    product_cat1_kg: float | None,
) -> list[CategoryResult]:
    results: list[CategoryResult] = []
    for category, clfs in buckets.items():
        line_sum = sum(c.kg_co2e for c in clfs if c.kg_co2e is not None)

        if category == 1 and product_cat1_kg is not None:
            # Reconcile: product rollup REPLACES the spend estimate for Cat 1.
            method = "product_rollup"
            total = product_cat1_kg
        else:
            method = "spend"
            total = line_sum
            # Invariant: a spend-method category total == sum of its line kg.
            assert math.isclose(total, line_sum, rel_tol=1e-9)

        results.append(
            CategoryResult(
                scope3_category=category,
                category_name=SCOPE3_CATEGORY_NAMES[category],
                total_kg_co2e=total,
                line_count=len(clfs),
                method=method,
                low_confidence_count=sum(1 for c in clfs if c.flag_status == "low_confidence"),
                review_scope_count=sum(1 for c in clfs if c.flag_status == "review_scope"),
                classifications=clfs,
            )
        )

    # If products exist but no Cat-1 spend lines were present, still surface Cat 1
    # from the product rollup so the inventory reflects it.
    if product_cat1_kg is not None and 1 not in buckets:
        results.append(
            CategoryResult(
                scope3_category=1,
                category_name=SCOPE3_CATEGORY_NAMES[1],
                total_kg_co2e=product_cat1_kg,
                line_count=0,
                method="product_rollup",
            )
        )
    return results
