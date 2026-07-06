"""Consolidation multiplier tests — the worked 40%-JV example (research/2.2).

GreenJV boiler = 1,000 tCO2e gross; AcmeCorp holds 40%. The multiplier varies
2.5x across approaches, which is why the approach must be declared immutably at
the inventory level.
"""

from __future__ import annotations

import pytest

from s1_consolidation import compute_consolidation_multiplier as multiplier


def test_jv_no_control_across_approaches() -> None:
    kw = dict(equity_pct=40.0, entity_type="joint_venture")
    assert multiplier("equity_share", **kw).multiplier == pytest.approx(0.40)
    assert multiplier("financial_control", has_financial_control=False, **kw).multiplier == 0.0
    assert multiplier("operational_control", has_operational_control=False, **kw).multiplier == 0.0


def test_jv_sole_operator_variant() -> None:
    """Mgmt contract: 40% equity but operational control -> 100% under op control."""
    kw = dict(equity_pct=40.0, entity_type="joint_venture")
    assert multiplier("operational_control", has_operational_control=True, **kw).multiplier == 1.0
    assert multiplier("equity_share", **kw).multiplier == pytest.approx(0.40)
    assert multiplier("financial_control", has_financial_control=False, **kw).multiplier == 0.0


def test_financial_control_sole_vs_jointly_controlled() -> None:
    # Wholly owned + financial control -> 100%.
    assert multiplier(
        "financial_control", equity_pct=100.0,
        has_financial_control=True, entity_type="wholly_owned_subsidiary",
    ).multiplier == 1.0
    # Jointly controlled operation with financial control -> equity %.
    assert multiplier(
        "financial_control", equity_pct=40.0,
        has_financial_control=True, entity_type="jointly_controlled_operation",
    ).multiplier == pytest.approx(0.40)


def test_economic_interest_overrides_equity() -> None:
    r = multiplier("equity_share", equity_pct=40.0, economic_interest_pct=36.0)
    assert r.multiplier == pytest.approx(0.36)   # e.g. 90% of SubCo x 40% of JV


def test_multiplier_clamped_and_rationale_present() -> None:
    r = multiplier("equity_share", equity_pct=150.0)
    assert r.multiplier == 1.0
    assert r.rationale                              # audit note always populated


def test_unknown_approach_raises() -> None:
    with pytest.raises(ValueError):
        multiplier("made_up", equity_pct=50.0)
