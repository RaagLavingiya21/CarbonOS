"""Tests for Scope 2 regulatory disclosure generators (V1 compliance)."""

from __future__ import annotations

import pytest

from s2_reporting.compliance import (
    DisclosureContext,
    UnknownStandardError,
    build_csrd_e1,
    build_disclosure,
    build_sb253,
    disclosure_to_csv,
)
from s2_reporting.summary import ReportSummary


def _summary(**kw) -> ReportSummary:
    base = dict(
        entity="Acme Co",
        reporting_year=2025,
        location_based_tco2e=120.5,
        market_based_tco2e=90.0,
        consumption_mwh=250.0,
        data_coverage_pct=100.0,
        methodology="Dual-method per GHG Protocol Scope 2.",
        market_based_fallback=False,
    )
    base.update(kw)
    return ReportSummary(**base)


def _assured() -> DisclosureContext:
    return DisclosureContext(assurance_status="limited assurance obtained")


def _titles(disclosure) -> list[str]:
    return [s.title for s in disclosure.sections]


def _find_value(disclosure, label: str):
    for section in disclosure.sections:
        for item in section.items:
            if item.label == label:
                return item.value
    return None


# --- SB 253 ----------------------------------------------------------------


def test_sb253_has_dual_method_scope2() -> None:
    d = build_sb253(_summary(), _assured())
    assert d.standard == "sb253"
    assert "Scope 2 emissions (GHG Protocol dual method)" in _titles(d)
    assert _find_value(d, "Scope 2 location-based") == "120.500 tCO2e"
    assert _find_value(d, "Scope 2 market-based") == "90.000 tCO2e"


def test_sb253_clean_summary_is_assurance_ready() -> None:
    d = build_sb253(_summary(), _assured())
    assert d.readiness.ready is True
    assert d.readiness.blockers == []


# --- CSRD ESRS E1 ----------------------------------------------------------


def test_csrd_has_e1_6_and_e1_5_sections() -> None:
    d = build_csrd_e1(_summary(), _assured())
    assert "E1-6 Gross Scope 2 GHG emissions" in _titles(d)
    assert "E1-5 Energy consumption & mix" in _titles(d)
    assert _find_value(d, "Location-based") == "120.500 tCO2e"


def test_csrd_energy_mix_untracked_warns() -> None:
    d = build_csrd_e1(_summary(), _assured())  # renewable_mwh None by default
    assert _find_value(d, "Renewable share") == "not tracked"
    assert any("Renewable energy share" in w for w in d.readiness.warnings)


def test_csrd_energy_mix_computed_when_renewable_known() -> None:
    ctx = DisclosureContext(assurance_status="limited assurance obtained", renewable_mwh=100.0)
    d = build_csrd_e1(_summary(consumption_mwh=250.0), ctx)
    assert _find_value(d, "Renewable share") == "40%"
    assert not any("Renewable energy share" in w for w in d.readiness.warnings)


# --- readiness gate --------------------------------------------------------


def test_no_consumption_blocks() -> None:
    d = build_sb253(_summary(consumption_mwh=0.0), _assured())
    assert d.readiness.ready is False
    assert any("energy consumption" in b for b in d.readiness.blockers)


def test_low_coverage_blocks_below_floor() -> None:
    d = build_sb253(_summary(data_coverage_pct=40.0), _assured())
    assert d.readiness.ready is False


def test_mid_coverage_warns_but_ready() -> None:
    d = build_sb253(_summary(data_coverage_pct=80.0), _assured())
    assert d.readiness.ready is True
    assert any("assurance target" in w for w in d.readiness.warnings)


def test_market_fallback_warns() -> None:
    d = build_sb253(_summary(market_based_fallback=True), _assured())
    assert any("not substantiated by EACs" in w for w in d.readiness.warnings)
    # ...and the MB item is annotated.
    for section in d.sections:
        for item in section.items:
            if item.label == "Scope 2 market-based":
                assert item.note is not None


def test_unassured_context_warns() -> None:
    d = build_sb253(_summary(), DisclosureContext())  # default = "not yet assured"
    assert any("assurance pending" in w for w in d.readiness.warnings)


# --- dispatch + csv --------------------------------------------------------


def test_build_disclosure_dispatch_and_unknown() -> None:
    assert build_disclosure(_summary(), _assured(), "sb253").standard == "sb253"
    assert build_disclosure(_summary(), _assured(), "csrd_e1").standard == "csrd_e1"
    with pytest.raises(UnknownStandardError):
        build_disclosure(_summary(), _assured(), "tcfd")


def test_disclosure_to_csv_flattens_sections() -> None:
    csv_text = disclosure_to_csv(build_sb253(_summary(), _assured()))
    lines = csv_text.strip().splitlines()
    assert lines[0] == "section,field,value,note"
    assert any("Scope 2 location-based" in line for line in lines)
