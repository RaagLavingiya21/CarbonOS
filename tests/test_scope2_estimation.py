"""Tests for the documented estimation fallback (PRD 5.2)."""

from __future__ import annotations

import pytest

from s2_ingestion.estimation import (
    EstimationError,
    estimate_annual_electricity_mwh,
)


def test_estimate_retail_hand_calc() -> None:
    result = estimate_annual_electricity_mwh("retail", 20_000)
    # 14 kWh/sqft x 20,000 sqft = 280,000 kWh = 280 MWh
    assert result.annual_mwh == pytest.approx(280.0)
    assert result.intensity_kwh_per_sqft == pytest.approx(14.0)


def test_estimate_note_is_audit_labeled() -> None:
    note = estimate_annual_electricity_mwh("office", 5_000).method_note
    assert "ESTIMATE" in note
    assert "SAMPLE" in note  # discloses the intensity is a replaceable placeholder


def test_estimate_unknown_site_type_raises() -> None:
    with pytest.raises(EstimationError):
        estimate_annual_electricity_mwh("spaceport", 1_000)


def test_estimate_nonpositive_area_raises() -> None:
    with pytest.raises(EstimationError):
        estimate_annual_electricity_mwh("office", 0)
