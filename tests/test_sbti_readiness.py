"""Tests for obligations/sbti_readiness.py (Epic C / P.1.3, reused by Epic D).

Pure logic. Covers Category A/B classification (incl. three-valued uncertain),
V2.0 per-category >=5% coverage, V1.x aggregate coverage, and the honesty rule
that the V2.0 net-zero % is never hardcoded.
"""

from __future__ import annotations

from s3_obligations.models import ObligationProfile
from s3_obligations.sbti_readiness import assess_sbti_readiness, classify_category

# A CPG-style Scope 3 profile: Cat 1 dominant, Cat 4/11 material, Cat 6 tiny.
_INV = {1: 700.0, 4: 120.0, 6: 30.0, 11: 150.0}  # total 1000; pcts 70/12/3/15
_CAT_A = ObligationProfile(annual_revenue_usd=1_500_000_000, employee_count=3000)


def test_category_a_by_revenue_or_employees():
    assert classify_category(ObligationProfile(annual_revenue_usd=2e9)) == "A"
    assert classify_category(ObligationProfile(employee_count=600)) == "A"
    assert classify_category(ObligationProfile(annual_revenue_usd=5e8, employee_count=100)) == "B"


def test_category_uncertain_when_unknown():
    # Revenue unknown, employees unknown -> cannot classify.
    assert classify_category(ObligationProfile()) == "uncertain"
    # Employees below A but revenue unknown -> still could be A on revenue -> uncertain.
    assert classify_category(ObligationProfile(employee_count=100)) == "uncertain"


def test_v2_requires_every_category_over_5pct():
    r = assess_sbti_readiness(_CAT_A, _INV, version="v2.0", horizon="near_term")
    assert r.category_class == "A"
    assert r.scope3_target_mandatory is True
    assert r.base_year_assurance_required is True
    # Cats 1 (70%), 4 (12%), 11 (15%) are >=5%; Cat 6 (3%) is not.
    assert set(r.required_categories) == {1, 4, 11}
    assert 6 not in r.required_categories


def test_v2_coverage_gap_and_meets():
    # Cover only Cat 1 -> gap is 4 and 11.
    r = assess_sbti_readiness(_CAT_A, _INV, covered_categories={1}, version="v2.0")
    assert set(r.coverage_gap) == {4, 11}
    assert r.meets_requirement is False
    # Cover all required -> meets.
    r2 = assess_sbti_readiness(_CAT_A, _INV, covered_categories={1, 4, 11}, version="v2.0")
    assert r2.coverage_gap == []
    assert r2.meets_requirement is True


def test_v2_netzero_pct_not_hardcoded():
    r = assess_sbti_readiness(
        _CAT_A, _INV, covered_categories={1, 4, 11}, version="v2.0", horizon="net_zero"
    )
    assert r.meets_requirement is None  # unconfirmed, not asserted
    assert any("unconfirmed" in n.lower() for n in r.notes)


def test_v1_aggregate_coverage():
    # V1 near-term needs >=67%. Cover Cat 1 (70%) -> meets.
    r = assess_sbti_readiness(
        _CAT_A, _INV, covered_categories={1}, version="v1.3.1", horizon="near_term"
    )
    assert r.meets_requirement is True
    # Cover only Cat 4+11 (27%) -> below 67%.
    r2 = assess_sbti_readiness(_CAT_A, _INV, covered_categories={4, 11}, version="v1.3.1")
    assert r2.meets_requirement is False


def test_empty_inventory_is_undetermined():
    r = assess_sbti_readiness(_CAT_A, {}, version="v2.0")
    assert r.total_scope3_kg == 0
    assert r.meets_requirement is None
    assert any("no scope 3 inventory" in n.lower() for n in r.notes)


def test_percentages_sum_to_one():
    r = assess_sbti_readiness(_CAT_A, _INV, version="v2.0")
    assert abs(sum(c.pct_of_scope3 for c in r.category_coverage) - 1.0) < 1e-9


def test_determinism():
    a = assess_sbti_readiness(_CAT_A, _INV, covered_categories={1}, version="v2.0")
    b = assess_sbti_readiness(_CAT_A, _INV, covered_categories={1}, version="v2.0")
    assert a.coverage_gap == b.coverage_gap
    assert a.required_categories == b.required_categories
