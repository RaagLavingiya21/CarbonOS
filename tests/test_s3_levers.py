"""Tests for Epic I — levers, MAC curve, and green-claims (s3_levers/). Pure logic.

Claims focus: substantiate ONLY from primary-data-backed + assured figures
(spend-based refused); an offset-based EU B2C neutrality claim is PROHIBITED.
"""

from __future__ import annotations

from s3_levers.claims import assess_claim
from s3_levers.library import load_levers, match_levers
from s3_levers.mac import build_mac_curve, total_abatement_tco2e

# --- lever library ----------------------------------------------------------


def test_match_levers_by_category():
    levers = match_levers({1, 4})
    cats = {lev.category for lev in levers}
    assert cats <= {1, 4} and levers  # only requested categories


def test_subsector_filters_out_non_applicable():
    # regenerative_agriculture is food/beverage only.
    apparel = {lev.lever_id for lev in match_levers({1}, sub_sector="apparel")}
    food = {lev.lever_id for lev in match_levers({1}, sub_sector="food")}
    assert "regenerative_agriculture" not in apparel
    assert "regenerative_agriculture" in food


def test_all_levers_loaded():
    assert len(load_levers()) >= 8


# --- MAC curve --------------------------------------------------------------


def test_mac_sorted_by_cost_and_cumulative():
    levers = match_levers({1, 4, 11})
    totals = {1: 700.0, 4: 120.0, 11: 150.0}  # tCO2e
    points = build_mac_curve(levers, totals)
    costs = [p.cost_per_tco2e for p in points]
    assert costs == sorted(costs)  # cheapest first
    # cumulative is non-decreasing and ends at the total abatement
    cums = [p.cumulative_abatement_tco2e for p in points]
    assert cums == sorted(cums)
    assert cums[-1] == total_abatement_tco2e(points)


def test_abatement_scales_with_category_total():
    levers = [lev for lev in load_levers() if lev.lever_id == "low_carbon_materials"]
    p_small = build_mac_curve(levers, {1: 100.0})[0]
    p_big = build_mac_curve(levers, {1: 1000.0})[0]
    assert p_big.abatement_tco2e == p_small.abatement_tco2e * 10


# --- claims: substantiation guard -------------------------------------------


def test_spend_based_claim_is_refused():
    a = assess_claim("Our product is low carbon", primary_data_share=0.0, assured=True)
    assert a.substantiable is False
    assert "primary" in a.substantiation_reason.lower()


def test_primary_data_backed_and_assured_is_substantiable():
    a = assess_claim("Our product is low carbon", primary_data_share=0.8, assured=True)
    assert a.substantiable is True


def test_primary_data_but_unassured_is_not_substantiable():
    a = assess_claim("Our product is low carbon", primary_data_share=0.8, assured=False)
    assert a.substantiable is False
    assert "assurance" in a.substantiation_reason.lower()


# --- claims: compliance flags -----------------------------------------------


def test_offset_based_neutrality_prohibited_in_eu():
    a = assess_claim(
        "This product is carbon neutral",
        primary_data_share=0.9,
        assured=True,
        jurisdiction="EU",
        offset_based=True,
    )
    assert any(f.verdict == "prohibited" for f in a.flags)
    assert a.substantiable is False  # prohibited overrides good evidence


def test_non_offset_neutrality_not_prohibited_by_empco():
    a = assess_claim(
        "This product is carbon neutral (in-value-chain reductions)",
        primary_data_share=0.9,
        assured=True,
        jurisdiction="EU",
        offset_based=False,
    )
    assert not any(f.rule_id == "empco_offset_neutrality_b2c" for f in a.flags)


def test_ruleset_version_recorded():
    a = assess_claim("green product", jurisdiction="EU")
    assert a.ruleset_version == "v2026-07"


def test_determinism():
    a = assess_claim("carbon neutral", primary_data_share=0.9, assured=True, offset_based=True)
    b = assess_claim("carbon neutral", primary_data_share=0.9, assured=True, offset_based=True)
    assert a.substantiable == b.substantiable and len(a.flags) == len(b.flags)
