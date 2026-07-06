"""Tests for data-quality / coverage scoring (PRD 5.6)."""

from __future__ import annotations

import pytest

from s2_quality.scoring import classify_source, compute_coverage


def _bill(site_id: int, mwh, *, estimated: bool = False, method: str = "csv") -> dict:
    return {
        "site_id": site_id,
        "canonical_mwh": mwh,
        "is_estimated_read": estimated,
        "ingestion_method": method,
    }


def test_classify_source() -> None:
    assert classify_source(_bill(1, 10)) == "actual"
    assert classify_source(_bill(1, 10, estimated=True)) == "documented_estimate"
    assert classify_source(_bill(1, 10, method="estimate")) == "documented_estimate"


def test_coverage_mixed_actual_and_estimate() -> None:
    bills = [_bill(1, 80), _bill(1, 20, estimated=True), _bill(2, 50)]
    cov = compute_coverage(bills, [1, 2, 3])
    assert cov.total_mwh == pytest.approx(150.0)
    assert cov.coverage_fraction == pytest.approx(130 / 150)
    assert cov.estimation_fraction == pytest.approx(20 / 150)
    assert cov.sites_with_data == 2
    assert cov.sites_missing_data == 1  # site 3 has no bills
    site1 = next(s for s in cov.per_site if s.site_id == 1)
    assert site1.coverage_fraction == pytest.approx(0.8)  # 80 actual / 100 total


def test_coverage_empty_portfolio() -> None:
    cov = compute_coverage([], [1, 2])
    assert cov.total_mwh == 0.0
    assert cov.coverage_fraction == 0.0
    assert cov.sites_missing_data == 2


def test_coverage_ignores_cost_only_rows() -> None:
    cov = compute_coverage([_bill(1, None), _bill(1, 100)], [1])
    assert cov.total_mwh == pytest.approx(100.0)
    assert cov.coverage_fraction == pytest.approx(1.0)
