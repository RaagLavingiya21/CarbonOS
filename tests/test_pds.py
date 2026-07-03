from __future__ import annotations

import pytest

from calc.pds import compute_primary_data_share


def test_mixed_primary_and_secondary_line_items() -> None:
    line_items = [
        {"kg_co2e": 30.0, "data_source": "primary"},
        {"kg_co2e": 70.0, "data_source": "secondary"},
    ]
    assert compute_primary_data_share(line_items) == pytest.approx(0.3)


def test_no_primary_items_returns_zero() -> None:
    line_items = [
        {"kg_co2e": 50.0, "data_source": "secondary"},
        {"kg_co2e": 50.0, "data_source": "secondary"},
    ]
    assert compute_primary_data_share(line_items) == 0.0


def test_all_primary_returns_one() -> None:
    line_items = [
        {"kg_co2e": 10.0, "data_source": "primary"},
        {"kg_co2e": 20.0, "data_source": "primary"},
    ]
    assert compute_primary_data_share(line_items) == pytest.approx(1.0)


def test_empty_or_zero_total_returns_zero() -> None:
    assert compute_primary_data_share([]) == 0.0
    assert compute_primary_data_share([{"kg_co2e": None, "data_source": "primary"}]) == 0.0
    assert compute_primary_data_share([{"kg_co2e": 0.0, "data_source": "secondary"}]) == 0.0
