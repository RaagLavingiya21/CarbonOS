"""Phase 0 smoke tests for the Scope 2 module scaffold."""

from __future__ import annotations

import pytest

from s2_ingestion.normalize import (
    CANONICAL_UNIT,
    UnitConversionError,
    normalize_to_mwh,
)
from s2_sites.templates import SITE_TYPES, get_template


def test_canonical_unit_is_mwh() -> None:
    assert CANONICAL_UNIT == "MWh"


def test_kwh_normalizes_to_mwh_with_trail() -> None:
    result = normalize_to_mwh(1500, "kWh")
    assert result.canonical_mwh == pytest.approx(1.5)
    assert result.factor_mwh_per_unit == pytest.approx(0.001)
    assert "MWh" in result.conversion_note


def test_therm_normalizes() -> None:
    result = normalize_to_mwh(100, "therms")
    assert result.canonical_mwh == pytest.approx(2.93071)


def test_ambiguous_mbtu_is_rejected() -> None:
    with pytest.raises(UnitConversionError):
        normalize_to_mwh(10, "MBtu")


def test_unknown_unit_is_rejected() -> None:
    with pytest.raises(UnitConversionError):
        normalize_to_mwh(10, "bushels")


def test_every_site_type_has_a_template() -> None:
    for site_type in SITE_TYPES:
        assert get_template(site_type).site_type == site_type


def test_scope2_health_endpoint() -> None:
    from fastapi.testclient import TestClient

    from api.main import app
    from tests.conftest import AUTH_HEADERS

    client = TestClient(app)
    response = client.get("/api/scope2/health", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert response.json()["module"] == "scope2"


def test_scope2_site_templates_endpoint() -> None:
    from fastapi.testclient import TestClient

    from api.main import app
    from tests.conftest import AUTH_HEADERS

    client = TestClient(app)
    response = client.get("/api/scope2/site-templates", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert {t["site_type"] for t in body} == set(SITE_TYPES)


def test_scope2_health_requires_auth() -> None:
    from fastapi.testclient import TestClient

    from api.main import app

    client = TestClient(app)
    response = client.get("/api/scope2/health")
    assert response.status_code == 401
