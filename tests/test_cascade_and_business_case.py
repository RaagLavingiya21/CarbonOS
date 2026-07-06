"""Tests for cascade-exposure detection (P.1.4.b) and the business-case builder
(P.1.1.d). Pure logic, no DB/network."""

from __future__ import annotations

from obligations.business_case import build_business_case
from obligations.cascade import detect_cascade
from obligations.engine import evaluate
from obligations.models import ObligationProfile

_ICP = ObligationProfile(
    annual_revenue_usd=1_500_000_000,
    employee_count=3_000,
    is_us_entity=True,
    does_business_in_ca=True,
    eu_turnover_eur=0.0,
    key_customers=["Walmart", "Local Co-op"],
)


# --- cascade detection ------------------------------------------------------


def test_cascade_flags_regulated_buyer():
    signals = detect_cascade(_ICP)
    assert len(signals) == 1
    sig = signals[0]
    assert sig.matched_buyer == "Walmart"
    assert "CA SB 253" in sig.regimes
    assert "cascade" in sig.rationale.lower()


def test_cascade_ignores_unregulated_customer():
    signals = detect_cascade(ObligationProfile(key_customers=["Local Co-op", "Jane's Diner"]))
    assert signals == []


def test_cascade_matches_aliases_and_case_insensitive():
    signals = detect_cascade(ObligationProfile(key_customers=["TESCO PLC", "sam's club"]))
    names = {s.matched_buyer for s in signals}
    assert "Tesco" in names
    assert "Walmart" in names  # via the sam's club alias


def test_cascade_deterministic():
    a = detect_cascade(_ICP)
    b = detect_cascade(_ICP)
    assert [s.matched_buyer for s in a] == [s.matched_buyer for s in b]


# --- business case ----------------------------------------------------------


def test_business_case_summarizes_engine_output():
    result = evaluate(_ICP)
    bc = build_business_case(result, detect_cascade(_ICP))
    assert bc.applicable_count >= 3
    assert bc.primary_driver == "Customer / retailer data request"  # highest priority
    assert bc.nearest_deadline is not None
    assert bc.uncertain_count >= 1  # SB261 watch
    assert any("Scope 3" in s for s in bc.at_stake)


def test_business_case_includes_cascade_and_watch():
    result = evaluate(_ICP)
    bc = build_business_case(result, detect_cascade(_ICP))
    assert any("Walmart" in c for c in bc.cascade_exposure)
    assert any("SB 261" in w for w in bc.watch_items)


def test_business_case_headline_mentions_nearest_deadline():
    result = evaluate(_ICP)
    bc = build_business_case(result, detect_cascade(_ICP))
    assert bc.nearest_deadline[0] in bc.headline
    assert "driver" in bc.headline.lower()


def test_business_case_empty_profile_has_no_drivers():
    result = evaluate(ObligationProfile())  # everything unknown/false
    bc = build_business_case(result, [])
    # No applicable drivers; headline should not fabricate deadlines.
    assert bc.applicable_count == 0
    assert bc.primary_driver is None


def test_business_case_numbers_come_from_engine():
    """No fabricated deadlines: every at-stake/deadline traces to the engine."""
    result = evaluate(_ICP)
    bc = build_business_case(result, detect_cascade(_ICP))
    engine_frameworks = {o.framework for o in result.applicable}
    # primary driver is one the engine actually returned as applicable
    assert bc.primary_driver in engine_frameworks
    # nearest deadline date appears in the engine timeline
    assert bc.nearest_deadline in result.timeline
