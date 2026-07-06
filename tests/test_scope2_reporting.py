"""Tests for M3 reporting — one number, many formats (PRD 5.5)."""

from __future__ import annotations

import pytest

from s2_reporting.formats import (
    DESTINATIONS,
    UnknownDestinationError,
    build_report,
    report_to_csv,
)
from s2_reporting.summary import build_summary


def _calc(**kw) -> dict:
    c = {
        "reporting_year": 2024,
        "location_based_kg_co2e": 4625.0,
        "market_based_kg_co2e": 7000.0,
        "consumption_mwh": 12.5,
        "methodology_notes": "GHG Protocol Scope 2 dual-method.",
        "factor_versions": {},
    }
    c.update(kw)
    return c


def test_build_summary_converts_kg_to_tonnes() -> None:
    s = build_summary(_calc(), entity="Acme", coverage_fraction=0.9)
    assert s.location_based_tco2e == pytest.approx(4.625)
    assert s.market_based_tco2e == pytest.approx(7.0)
    assert s.data_coverage_pct == pytest.approx(90.0)
    assert s.entity == "Acme"


def test_all_destinations_configured() -> None:
    assert set(DESTINATIONS) == {"standard", "cdp", "amazon"}


def test_cdp_report_has_both_methods() -> None:
    s = build_summary(_calc(), entity="Acme", coverage_fraction=1.0)
    labels = [r["field"].lower() for r in build_report(s, "cdp")]
    assert any("location-based" in label for label in labels)
    assert any("market-based" in label for label in labels)


def test_amazon_report_requires_both_methods() -> None:
    s = build_summary(_calc(), entity="Acme", coverage_fraction=1.0)
    labels = [r["field"].lower() for r in build_report(s, "amazon")]
    assert any("location-based" in label for label in labels)
    assert any("market-based" in label for label in labels)


def test_unknown_destination_raises() -> None:
    s = build_summary(_calc(), entity="Acme", coverage_fraction=1.0)
    with pytest.raises(UnknownDestinationError):
        build_report(s, "bogus")


def test_report_csv_serializes() -> None:
    s = build_summary(_calc(), entity="Acme", coverage_fraction=1.0)
    csv_text = report_to_csv(build_report(s, "standard"))
    assert "field,value" in csv_text
    assert "Acme" in csv_text
