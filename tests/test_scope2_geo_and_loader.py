"""Tests for eGRID geo-mapping and the factor-seeding loader (PRD 5.3 / 5.4)."""

from __future__ import annotations

import pytest

from s2_sites.geomap import (
    EGRID_SUBREGIONS,
    country_to_iea,
    is_valid_subregion,
)
from scripts.seed_s2_factors import FactorCsvError, parse_factor_csv

_HEADER = "factor_type,region_code,vintage_year,kg_co2e_per_mwh,source_citation\n"


# --- geomap ---------------------------------------------------------------


def test_subregion_registry_populated() -> None:
    assert len(EGRID_SUBREGIONS) >= 20
    assert {"RFCE", "CAMX", "ERCT"} <= set(EGRID_SUBREGIONS)


def test_is_valid_subregion_case_insensitive() -> None:
    assert is_valid_subregion("rfce")
    assert is_valid_subregion(" ERCT ")
    assert not is_valid_subregion("ZZZZ")


def test_country_to_iea_normalizes() -> None:
    assert country_to_iea(" us ") == "US"


# --- factor loader --------------------------------------------------------


def test_parse_factor_csv_valid() -> None:
    rows = parse_factor_csv(_HEADER + "egrid,RFCE,2024,320,EPA eGRID 2024\n")
    assert rows[0]["factor_type"] == "egrid"
    assert rows[0]["region_code"] == "RFCE"
    assert rows[0]["kg_co2e_per_mwh"] == pytest.approx(320.0)
    assert rows[0]["source_citation"] == "EPA eGRID 2024"


def test_parse_factor_csv_missing_column() -> None:
    with pytest.raises(FactorCsvError):
        parse_factor_csv("factor_type,region_code\negrid,RFCE\n")


def test_parse_factor_csv_rejects_unknown_type() -> None:
    with pytest.raises(FactorCsvError):
        parse_factor_csv(_HEADER + "bogus,RFCE,2024,320,cite\n")


def test_parse_factor_csv_requires_citation() -> None:
    with pytest.raises(FactorCsvError):
        parse_factor_csv(_HEADER + "egrid,RFCE,2024,320,\n")


def test_parse_factor_csv_rejects_empty() -> None:
    with pytest.raises(FactorCsvError):
        parse_factor_csv(_HEADER)


def test_template_csv_parses() -> None:
    from pathlib import Path

    template = (
        Path(__file__).resolve().parent.parent / "scripts" / "s2_factors_template.csv"
    )
    rows = parse_factor_csv(template.read_text())
    assert len(rows) >= 4
    assert all(r["source_citation"] for r in rows)
