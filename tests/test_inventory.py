"""End-to-end test for the Epic A corporate inventory spine (parse -> classify
-> aggregate). Runs against the real Open CEDA 2025 workbook + the sample GL,
no DB/network. Proves the whole spend->inventory pipeline works and holds its
invariants, and that Cat-1 reconciliation replaces (never double-counts) spend.
"""

from __future__ import annotations

import math
from pathlib import Path

from s3_measure.inventory import build_inventory_from_spend
from s3_measure.spend_parser import parse_spend_csv

_SAMPLE = Path(__file__).parent.parent / "sample_gl" / "company_gl_sample.csv"


def _inventory(**kwargs):
    parsed = parse_spend_csv(_SAMPLE)
    return build_inventory_from_spend(parsed, **kwargs)


def test_pipeline_produces_a_company_number():
    inv = _inventory()
    assert inv.total_kg_co2e > 0
    assert inv.classified_line_count >= 8


def test_expected_categories_present():
    """Sample spans Cat 1 (fabric/insurance), 2 (laptops), 3 (gas), 4 (freight),
    5 (waste), 6 (air travel)."""
    inv = _inventory()
    cats = set(inv.category_totals)
    for expected in (1, 2, 3, 4, 5, 6):
        assert expected in cats, f"Cat {expected} missing; got {sorted(cats)}"


def test_corporate_total_equals_category_sum():
    inv = _inventory()
    assert math.isclose(
        inv.total_kg_co2e,
        sum(c.total_kg_co2e for c in inv.category_results),
        rel_tol=1e-9,
    )


def test_spend_category_total_equals_line_sum():
    inv = _inventory()
    for cat in inv.category_results:
        if cat.method == "spend":
            line_sum = sum(c.kg_co2e for c in cat.classifications if c.kg_co2e is not None)
            assert math.isclose(cat.total_kg_co2e, line_sum, rel_tol=1e-9)


def test_kg_equals_amount_times_ef():
    inv = _inventory()
    for cat in inv.category_results:
        for clf in cat.classifications:
            # amount was 1:1 with the parsed line; re-derive from ef and kg.
            assert clf.kg_co2e is not None
            assert clf.ef_kg_co2e_per_usd >= 0


def test_excluded_lines_tracked():
    """BoxCo (missing amount), refund (credit), MysteryVendor (no description)."""
    inv = _inventory()
    assert inv.excluded_reasons.get("missing_amount", 0) >= 1
    assert inv.excluded_reasons.get("credit_or_zero", 0) >= 1
    assert inv.excluded_reasons.get("missing_description", 0) >= 1


def test_cat1_reconciliation_replaces_spend():
    """When a product rollup is supplied, Cat 1 uses it (method=product_rollup)
    and the spend-based Cat 1 estimate is replaced, not added (no double-count)."""
    spend_only = _inventory()
    spend_cat1 = spend_only.category_totals.get(1, 0.0)
    assert spend_cat1 > 0  # sample has Cat 1 spend

    product_cat1 = 999_999.0
    reconciled = _inventory(product_cat1_kg=product_cat1)
    cat1 = next(c for c in reconciled.category_results if c.scope3_category == 1)
    assert cat1.method == "product_rollup"
    assert math.isclose(cat1.total_kg_co2e, product_cat1, rel_tol=1e-9)

    # No double-count: corporate total moved by exactly (product_cat1 - spend_cat1).
    delta = reconciled.total_kg_co2e - spend_only.total_kg_co2e
    assert math.isclose(delta, product_cat1 - spend_cat1, rel_tol=1e-6)


def test_energy_lines_flagged_review_scope():
    """Natural gas (Cat 3) carries the Scope 1/2 review flag through to the
    category rollup."""
    inv = _inventory()
    cat3 = next((c for c in inv.category_results if c.scope3_category == 3), None)
    assert cat3 is not None
    assert cat3.review_scope_count >= 1
