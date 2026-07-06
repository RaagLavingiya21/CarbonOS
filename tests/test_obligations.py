"""Tests for the Epic C obligation engine (obligations/).

Pure logic, no DB/network. Asserts the plan's invariants: correct Category A /
SB253 detection for the ICP, uncertainty kept honest (SB261 injunction, missing
data), version stamping, determinism, and that no fabricated fixed values are
emitted for in-flux rules (SBTi net-zero %).
"""

from __future__ import annotations

import pytest

from s3_obligations.engine import evaluate
from s3_obligations.models import ObligationProfile
from s3_obligations.ruleset import RulesetError, load_ruleset

# A typical ICP: US consumer brand, large by revenue, sells to Walmart, no EU
# nexus. eu_turnover_eur=0 is a KNOWN zero (not None/unknown) so CSRD resolves to
# a definite not-applicable rather than uncertain.
_ICP = ObligationProfile(
    annual_revenue_usd=1_500_000_000,
    employee_count=3_000,
    is_us_entity=True,
    does_business_in_ca=True,
    eu_turnover_eur=0.0,
    sector="apparel",
    key_customers=["Walmart", "Target"],
)


def _ids(obligations) -> set[str]:
    return {o.rule_id for o in obligations}


def test_icp_is_sb253_and_sbti_category_a():
    r = evaluate(_ICP)
    assert "ca_sb253" in _ids(r.applicable)
    assert "sbti_v2_category_a" in _ids(r.applicable)
    # SBTi obligation flags mandatory Scope 3 + base-year assurance.
    sbti = next(o for o in r.applicable if o.rule_id == "sbti_v2_category_a")
    assert sbti.assurance and "assurance" in sbti.assurance.lower()


def test_customer_request_routes_and_ranks_top():
    r = evaluate(_ICP)
    assert "customer_retailer_request" in _ids(r.applicable)
    # Highest priority → surfaced first.
    assert r.applicable[0].rule_id == "customer_retailer_request"


def test_sb261_is_uncertain_not_asserted():
    """SB261 matches on revenue but enforcement is under injunction → uncertain."""
    r = evaluate(_ICP)
    assert "ca_sb261" in _ids(r.uncertain)
    assert "ca_sb261" not in _ids(r.applicable)


def test_missing_revenue_yields_uncertain_not_false():
    """Three-valued honesty: unknown revenue must not silently drop SB253."""
    profile = ObligationProfile(
        employee_count=3_000, is_us_entity=True, does_business_in_ca=True
    )  # revenue None
    r = evaluate(profile)
    assert "ca_sb253" in _ids(r.uncertain)
    assert "ca_sb253" not in _ids(r.not_applicable)
    # But SBTi still applies via the >500-employee branch (any-of).
    assert "sbti_v2_category_a" in _ids(r.applicable)


def test_us_only_brand_not_caught_by_csrd():
    r = evaluate(_ICP)  # no EU turnover
    assert "csrd_esrs_e1" in _ids(r.not_applicable)


def test_eu_exposed_brand_caught_by_csrd():
    profile = ObligationProfile(
        employee_count=1_500,
        eu_turnover_eur=600_000_000,
        eu_subsidiary=True,
    )
    r = evaluate(profile)
    assert "csrd_esrs_e1" in _ids(r.applicable)


def test_sbti_netzero_pct_not_hardcoded():
    """The in-flux net-zero coverage % must stay unconfirmed, not fabricated."""
    r = evaluate(_ICP)
    sbti = next(o for o in r.applicable if o.rule_id == "sbti_v2_category_a")
    assert sbti.confidence == "partial"
    text = (sbti.assurance or "") + " ".join(d.note or "" for d in sbti.due)
    assert "unconfirmed" in text.lower()


def test_every_obligation_has_citation_and_version():
    r = evaluate(_ICP)
    for o in r.applicable + r.uncertain + r.not_applicable:
        assert o.citation, f"{o.rule_id} missing citation"
        assert o.ruleset_version == "v2026-07"
        assert o.threshold_detail


def test_timeline_sorted_by_date():
    r = evaluate(_ICP)
    dates = [t[0] for t in r.timeline]
    assert dates == sorted(dates)
    assert dates, "expected at least one dated obligation"


def test_determinism():
    a = evaluate(_ICP)
    b = evaluate(_ICP)
    assert _ids(a.applicable) == _ids(b.applicable)
    assert [o.rule_id for o in a.applicable] == [o.rule_id for o in b.applicable]


def test_unknown_ruleset_version_raises():
    with pytest.raises(RulesetError):
        load_ruleset("v1999-01")
