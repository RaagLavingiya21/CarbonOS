"""Tests for Epic F supplier cohorting + scorecards (s3_suppliers/). Pure logic."""

from __future__ import annotations

from s3_suppliers.cohorting import build_cohort, rank_suppliers
from s3_suppliers.models import Supplier
from s3_suppliers.scorecard import program_scorecard

_SUPPLIERS = [
    Supplier(
        "s1",
        "BigCotton",
        1,
        emissions_kg=5000,
        spend_usd=100000,
        pcf_received=True,
        dq_score=80,
        supplier_sbt_status="committed",
    ),
    Supplier("s2", "SmallDye", 1, emissions_kg=500, spend_usd=20000, pcf_received=False),
    Supplier(
        "s3",
        "Freighter",
        4,
        emissions_kg=2000,
        spend_usd=50000,
        pcf_received=True,
        dq_score=60,
        supplier_sbt_status="validated",
    ),
    Supplier("s4", "TinyPkg", 1, emissions_kg=300, spend_usd=8000, pcf_received=False),
]


def test_rank_by_emissions_desc():
    ranked = rank_suppliers(_SUPPLIERS, basis="emissions")
    assert [s.supplier_id for s in ranked] == ["s1", "s3", "s2", "s4"]


def test_rank_by_spend_differs():
    ranked = rank_suppliers(_SUPPLIERS, basis="spend")
    assert ranked[0].supplier_id == "s1"  # highest spend
    assert [s.supplier_id for s in ranked] == ["s1", "s3", "s2", "s4"]


def test_cohort_targets_hotspot_categories_only():
    cohort = build_cohort(_SUPPLIERS, {1}, top_n=10)
    assert all(s.scope3_category == 1 for s in cohort.members)
    assert {s.supplier_id for s in cohort.members} == {"s1", "s2", "s4"}


def test_cohort_top_n_and_coverage():
    # Cat 1 emissions total = 5000+500+300 = 5800; top-1 = 5000 -> ~86%.
    cohort = build_cohort(_SUPPLIERS, {1}, top_n=1)
    assert len(cohort.members) == 1 and cohort.members[0].supplier_id == "s1"
    assert abs(cohort.emissions_covered_pct - 5000 / 5800) < 1e-4


def test_scorecard_metrics():
    sc = program_scorecard(_SUPPLIERS)
    assert sc.supplier_count == 4
    assert sc.pcf_coverage_pct == 0.5  # 2 of 4 have PCFs
    # emissions covered = (5000+2000)/(5000+500+2000+300) = 7000/7800
    assert abs(sc.emissions_covered_pct - 7000 / 7800) < 1e-4
    assert sc.avg_dq == 70.0  # mean of 80, 60
    assert sc.sbt_committed_count == 1 and sc.sbt_validated_count == 1


def test_empty_scorecard_is_safe():
    sc = program_scorecard([])
    assert sc.supplier_count == 0 and sc.avg_dq is None


def test_determinism():
    a = build_cohort(_SUPPLIERS, {1, 4}, top_n=2)
    b = build_cohort(_SUPPLIERS, {1, 4}, top_n=2)
    assert [s.supplier_id for s in a.members] == [s.supplier_id for s in b.members]
