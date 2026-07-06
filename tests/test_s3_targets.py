"""Tests for the Scope-3 SBTi/FLAG target wizard math (Epic D). Pure logic."""

from __future__ import annotations

import pytest

from s3_obligations.models import ObligationProfile
from s3_targets.flag import assess_flag, is_flag_sector
from s3_targets.wizard import (
    build_draft_target,
    build_target_trajectory,
    check_ambition,
    sbti_reference_reduction,
)

_CAT_A = ObligationProfile(annual_revenue_usd=1_500_000_000, employee_count=3000)
_INV = {1: 700.0, 4: 120.0, 6: 30.0, 11: 150.0}  # total 1000


# --- trajectory -------------------------------------------------------------


def test_absolute_trajectory_endpoints_and_length():
    traj = build_target_trajectory(2025, 1000.0, 2030, 0.42)
    assert traj.points[0].year == 2025
    assert traj.points[0].target_kg_co2e == 1000.0
    assert traj.points[-1].year == 2030
    assert traj.target_kg_co2e == pytest.approx(580.0)  # 1000 * (1 - 0.42)
    assert len(traj.points) == 6  # 2025..2030 inclusive


def test_trajectory_is_monotonic_decreasing():
    traj = build_target_trajectory(2025, 1000.0, 2035, 0.5)
    vals = [p.target_kg_co2e for p in traj.points]
    assert vals == sorted(vals, reverse=True)


def test_trajectory_validates_years_and_pct():
    with pytest.raises(ValueError):
        build_target_trajectory(2030, 1000.0, 2025, 0.4)  # target before base
    with pytest.raises(ValueError):
        build_target_trajectory(2025, 1000.0, 2030, 1.5)  # pct out of range


# --- ambition (reference, not gospel) ---------------------------------------


def test_reference_reduction_uses_labeled_aca_rate():
    # ~4.2%/yr over 10 years ~ 42%.
    assert sbti_reference_reduction(2025, 2035) == pytest.approx(0.42, abs=1e-9)


def test_ambition_check_flags_below_reference_and_notes_verify():
    low = check_ambition(0.20, 2025, 2035)  # 20% < ~42% reference
    assert low.meets_reference is False
    assert "verify" in low.note.lower()
    high = check_ambition(0.50, 2025, 2035)
    assert high.meets_reference is True


# --- FLAG -------------------------------------------------------------------


def test_flag_required_by_sector():
    a = assess_flag("Food and beverage", total_kg_co2e=1000, flag_kg_co2e=0)
    assert a.is_flag_required is True
    assert a.no_deforestation_commitment_date == "2025-12-31"


def test_flag_required_by_share_over_20pct():
    a = assess_flag("consumer electronics", total_kg_co2e=1000, flag_kg_co2e=250)
    assert a.is_flag_required is True
    assert a.flag_share == pytest.approx(0.25)


def test_flag_not_required_below_threshold_nonflag_sector():
    a = assess_flag("consumer electronics", total_kg_co2e=1000, flag_kg_co2e=100)
    assert a.is_flag_required is False
    assert a.no_deforestation_commitment_date is None


def test_is_flag_sector_keywords():
    assert is_flag_sector("apparel textile manufacturing")
    assert not is_flag_sector("software services")


# --- draft target (composition, reuses C4) ----------------------------------


def test_draft_target_composes_readiness_trajectory_flag():
    dt = build_draft_target(
        _CAT_A,
        _INV,
        base_year=2025,
        target_year=2030,
        reduction_pct=0.42,
        covered_categories={1, 4, 11},
        version="v2.0",
        sector="Food and beverage",
    )
    # C4 readiness carried through
    assert dt.readiness.category_class == "A"
    assert dt.readiness.meets_requirement is True  # all >=5% cats covered
    # trajectory anchored on the inventory total (1000)
    assert dt.trajectory.base_kg_co2e == pytest.approx(1000.0)
    assert dt.trajectory.target_kg_co2e == pytest.approx(580.0)
    # FLAG triggered by the food sector
    assert dt.flag is not None and dt.flag.is_flag_required is True


def test_draft_target_netzero_pct_stays_unconfirmed():
    dt = build_draft_target(
        _CAT_A,
        _INV,
        base_year=2025,
        target_year=2050,
        reduction_pct=0.90,
        covered_categories={1, 4, 11},
        version="v2.0",
        horizon="net_zero",
    )
    assert dt.readiness.meets_requirement is None
    assert any("unconfirmed" in n.lower() for n in dt.notes)


def test_draft_target_determinism():
    kw = dict(base_year=2025, target_year=2030, reduction_pct=0.42, covered_categories={1})
    a = build_draft_target(_CAT_A, _INV, **kw)
    b = build_draft_target(_CAT_A, _INV, **kw)
    assert [p.target_kg_co2e for p in a.trajectory.points] == [
        p.target_kg_co2e for p in b.trajectory.points
    ]
    assert a.readiness.coverage_gap == b.readiness.coverage_gap
