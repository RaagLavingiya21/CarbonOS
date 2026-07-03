from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.skills.analysis import analysis_skill
from db import scenario_store as scenario_store_module
from factors.ef_lookup import EFMatch
from tests.conftest import AUTH_HEADERS, TEST_ACCESS_TOKEN, TEST_USER_ID

client = TestClient(app)

BASELINE_PRODUCT = {
    "product_id": 1,
    "product_name": "Test Product",
    "total_kg_co2e": 30.0,
    "line_items": [
        {
            "item_id": 10,
            "component": "body",
            "material": "aluminium",
            "spend_usd": 10.0,
            "matched_sector": "Aluminium",
            "emission_factor": 2.0,
            "ef_source": "Open CEDA",
            "kg_co2e": 20.0,
            "share_pct": 66.6667,
        },
        {
            "item_id": 11,
            "component": "cap",
            "material": "plastic",
            "spend_usd": 5.0,
            "matched_sector": "Plastic",
            "emission_factor": 2.0,
            "ef_source": "Open CEDA",
            "kg_co2e": 10.0,
            "share_pct": 33.3333,
        },
    ],
}


@dataclass
class InMemoryScenarioDb:
    scenarios: dict[int, dict[str, Any]] = field(default_factory=dict)
    scenario_items: dict[int, dict[str, Any]] = field(default_factory=dict)
    product_updates: list[dict[str, Any]] = field(default_factory=list)
    line_item_updates: list[dict[str, Any]] = field(default_factory=list)
    next_scenario_id: int = 1
    next_item_id: int = 1

    def table(self, name: str) -> MagicMock:
        db = self
        mock_table = MagicMock()

        if name == "scenarios":

            def insert(data: dict | list[dict]) -> MagicMock:
                rows = data if isinstance(data, list) else [data]
                inserted = []
                for row in rows:
                    scenario_id = db.next_scenario_id
                    db.next_scenario_id += 1
                    stored = {**row, "scenario_id": scenario_id, "created_at": "2026-01-01T00:00:00Z"}
                    db.scenarios[scenario_id] = stored
                    inserted.append(stored)
                mock_insert = MagicMock()
                mock_insert.execute = MagicMock(return_value=MagicMock(data=inserted))
                return mock_insert

            def select(columns: str) -> MagicMock:
                query = MagicMock()

                def eq(column: str, value: Any) -> MagicMock:
                    chained = MagicMock()

                    def limit(count: int) -> MagicMock:
                        result = MagicMock()
                        if column == "scenario_id" and value in db.scenarios:
                            result.data = [db.scenarios[value]]
                        elif column == "baseline_product_id":
                            result.data = [
                                s for s in db.scenarios.values() if s["baseline_product_id"] == value
                            ]
                        else:
                            result.data = []
                        result.execute = MagicMock(return_value=result)
                        return result

                    def order(col: str, *, desc: bool = False, nullsfirst: bool = False) -> MagicMock:
                        ordered = MagicMock()
                        ordered.execute = MagicMock(
                            return_value=MagicMock(
                                data=sorted(
                                    [s for s in db.scenarios.values() if s.get("baseline_product_id") == value],
                                    key=lambda s: s.get("created_at", ""),
                                    reverse=desc,
                                )
                            )
                        )
                        return ordered

                    chained.limit = limit
                    chained.order = order
                    chained.execute = MagicMock(return_value=MagicMock(data=[]))
                    return chained

                query.eq = eq
                return query

            def update(data: dict) -> MagicMock:
                db.product_updates.append(data)
                updater = MagicMock()

                def eq(column: str, value: Any) -> MagicMock:
                    if column == "scenario_id" and value in db.scenarios:
                        db.scenarios[value].update(data)
                    finisher = MagicMock()
                    finisher.execute = MagicMock(return_value=MagicMock(data=[]))
                    return finisher

                updater.eq = eq
                return updater

            def delete() -> MagicMock:
                deleter = MagicMock()

                def eq(column: str, value: Any) -> MagicMock:
                    if column == "scenario_id" and value in db.scenarios:
                        del db.scenarios[value]
                        for item_id in list(db.scenario_items):
                            if db.scenario_items[item_id]["scenario_id"] == value:
                                del db.scenario_items[item_id]
                    finisher = MagicMock()
                    finisher.execute = MagicMock(return_value=MagicMock(data=[]))
                    return finisher

                deleter.eq = eq
                return deleter

            mock_table.insert = insert
            mock_table.select = select
            mock_table.update = update
            mock_table.delete = delete

        elif name == "scenario_line_items":

            def insert(data: dict | list[dict]) -> MagicMock:
                rows = data if isinstance(data, list) else [data]
                inserted = []
                for row in rows:
                    item_id = db.next_item_id
                    db.next_item_id += 1
                    stored = {**row, "scenario_item_id": item_id}
                    db.scenario_items[item_id] = stored
                    inserted.append(stored)
                mock_insert = MagicMock()
                mock_insert.execute = MagicMock(return_value=MagicMock(data=inserted))
                return mock_insert

            def select(columns: str) -> MagicMock:
                query = MagicMock()

                def eq(column: str, value: Any) -> MagicMock:
                    chained = MagicMock()

                    def limit(count: int) -> MagicMock:
                        result = MagicMock()
                        if column == "scenario_item_id" and value in db.scenario_items:
                            result.data = [db.scenario_items[value]]
                        else:
                            result.data = []
                        result.execute = MagicMock(return_value=result)
                        return result

                    def order(col: str, *, desc: bool = False, nullsfirst: bool = False) -> MagicMock:
                        ordered = MagicMock()
                        items = [
                            li
                            for li in db.scenario_items.values()
                            if li.get("scenario_id") == value
                        ]
                        items.sort(key=lambda li: li.get("share_pct") or 0, reverse=desc)
                        ordered.execute = MagicMock(return_value=MagicMock(data=items))
                        return ordered

                    chained.limit = limit
                    chained.order = order
                    chained.execute = MagicMock(return_value=MagicMock(data=[]))
                    return chained

                query.eq = eq
                return query

            def update(data: dict) -> MagicMock:
                db.line_item_updates.append(data)
                updater = MagicMock()

                def eq(column: str, value: Any) -> MagicMock:
                    if column == "scenario_item_id" and value in db.scenario_items:
                        db.scenario_items[value].update(data)
                    finisher = MagicMock()
                    finisher.execute = MagicMock(return_value=MagicMock(data=[]))
                    return finisher

                updater.eq = eq
                return updater

            mock_table.insert = insert
            mock_table.select = select
            mock_table.update = update

        elif name == "products":

            def update(data: dict) -> MagicMock:
                db.product_updates.append(data)
                return MagicMock(eq=MagicMock(return_value=MagicMock(execute=MagicMock())))

            mock_table.update = update

        elif name == "line_items":

            def update(data: dict) -> MagicMock:
                db.line_item_updates.append(data)
                return MagicMock(eq=MagicMock(return_value=MagicMock(execute=MagicMock())))

            mock_table.update = update

        return mock_table


def _install_scenario_mocks(monkeypatch: pytest.MonkeyPatch) -> InMemoryScenarioDb:
    db = InMemoryScenarioDb()
    mock_client = MagicMock()
    mock_client.table.side_effect = db.table
    monkeypatch.setattr(scenario_store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(
        scenario_store_module,
        "get_product_by_id",
        lambda product_id, access_token: BASELINE_PRODUCT if product_id == 1 else None,
    )
    return db


def _fake_lookup_ef(material: str, country: str | None = None) -> EFMatch:
    return EFMatch(
        material_input=material,
        sector_name="Recycled Aluminium",
        sector_code="3313",
        ef_kg_co2e_per_usd=1.0,
        country_used="US",
        confidence_score=90.0,
        is_low_confidence=False,
        is_no_match=False,
        source_citation="Open CEDA 2025 - recycled aluminium",
        suggested_alternatives=[],
    )


def test_create_scenario_from_product_clones_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _install_scenario_mocks(monkeypatch)

    scenario_id = scenario_store_module.create_scenario_from_product(
        1,
        "Test scenario",
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )

    assert scenario_id == 1
    scenario = db.scenarios[scenario_id]
    assert scenario["baseline_total_kg_co2e"] == 30.0
    assert scenario["total_kg_co2e"] == 30.0
    assert len(db.scenario_items) == 2
    for item in db.scenario_items.values():
        assert item["baseline_material"] == item["material"]
        assert item["baseline_kg_co2e"] == item["kg_co2e"]
        assert item["is_edited"] is False


def test_edit_scenario_line_item_material_swap(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _install_scenario_mocks(monkeypatch)
    monkeypatch.setattr(scenario_store_module, "lookup_ef", _fake_lookup_ef)

    scenario_id = scenario_store_module.create_scenario_from_product(
        1,
        "Swap test",
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )
    item_id = next(iter(db.scenario_items))

    result = scenario_store_module.edit_scenario_line_item(
        item_id,
        material="recycled aluminium",
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )

    item = db.scenario_items[item_id]
    assert item["material"] == "recycled aluminium"
    assert item["kg_co2e"] == 10.0
    assert item["ef_source"] == "Open CEDA 2025 - recycled aluminium"
    assert item["is_edited"] is True
    assert result["scenario_total"] == sum(li["kg_co2e"] for li in db.scenario_items.values())
    assert db.scenarios[scenario_id]["total_kg_co2e"] == result["scenario_total"]


def test_edit_scenario_line_item_spend_edit(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _install_scenario_mocks(monkeypatch)

    scenario_store_module.create_scenario_from_product(
        1,
        "Spend test",
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )
    item_id = next(iter(db.scenario_items))
    original_ef = db.scenario_items[item_id]["emission_factor"]

    result = scenario_store_module.edit_scenario_line_item(
        item_id,
        spend_usd=5.0,
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )

    item = db.scenario_items[item_id]
    assert item["spend_usd"] == 5.0
    assert item["emission_factor"] == original_ef
    assert item["kg_co2e"] == 10.0
    assert result["scenario_total"] == sum(li["kg_co2e"] for li in db.scenario_items.values())


def test_scenario_total_equals_sum_of_line_items(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _install_scenario_mocks(monkeypatch)
    monkeypatch.setattr(scenario_store_module, "lookup_ef", _fake_lookup_ef)

    scenario_id = scenario_store_module.create_scenario_from_product(
        1,
        "Invariant test",
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )
    item_id = next(iter(db.scenario_items))
    scenario_store_module.edit_scenario_line_item(
        item_id,
        material="recycled aluminium",
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )

    total = db.scenarios[scenario_id]["total_kg_co2e"]
    line_sum = sum(li["kg_co2e"] for li in db.scenario_items.values())
    assert total == line_sum


def test_edit_scenario_never_mutates_baseline_products(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _install_scenario_mocks(monkeypatch)
    monkeypatch.setattr(scenario_store_module, "lookup_ef", _fake_lookup_ef)

    scenario_id = scenario_store_module.create_scenario_from_product(
        1,
        "Immutability test",
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )
    item_id = next(iter(db.scenario_items))
    scenario_store_module.edit_scenario_line_item(
        item_id,
        spend_usd=3.0,
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )

    product_only_updates = [u for u in db.product_updates if "status" in u or "product_name" in u]
    assert product_only_updates == []
    assert db.line_item_updates == [] or all("product_id" not in u for u in db.line_item_updates)
    assert db.scenarios[scenario_id]["total_kg_co2e"] != 30.0


def test_api_create_edit_get_returns_deltas(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _install_scenario_mocks(monkeypatch)
    monkeypatch.setattr(scenario_store_module, "lookup_ef", _fake_lookup_ef)
    monkeypatch.setattr(
        "api.routes.scenarios.get_product_by_id",
        lambda pid, token: BASELINE_PRODUCT if pid == 1 else None,
    )

    create_resp = client.post(
        "/api/products/1/scenarios",
        headers=AUTH_HEADERS,
        json={"name": "API scenario"},
    )
    assert create_resp.status_code == 200
    scenario_id = create_resp.json()["scenario_id"]
    item_id = next(iter(db.scenario_items))

    edit_resp = client.patch(
        f"/api/scenarios/{scenario_id}/line-items/{item_id}",
        headers=AUTH_HEADERS,
        json={"material": "recycled aluminium"},
    )
    assert edit_resp.status_code == 200
    edit_body = edit_resp.json()
    assert edit_body["delta_kg"] == edit_body["scenario_total"] - edit_body["baseline_total"]
    assert edit_body["item"]["ef_source"]

    get_resp = client.get(f"/api/scenarios/{scenario_id}", headers=AUTH_HEADERS)
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["delta_kg"] == edit_body["delta_kg"]
    assert detail["delta_pct"] == edit_body["delta_pct"]


def test_api_404_missing_product(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "api.routes.scenarios.get_product_by_id",
        lambda pid, token: None,
    )
    response = client.post(
        "/api/products/999/scenarios",
        headers=AUTH_HEADERS,
        json={"name": "Missing"},
    )
    assert response.status_code == 404


def test_api_404_missing_scenario(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _install_scenario_mocks(monkeypatch)
    mock_client = MagicMock()
    mock_client.table.side_effect = db.table
    monkeypatch.setattr(scenario_store_module, "get_user_client", lambda _token: mock_client)

    response = client.get("/api/scenarios/999", headers=AUTH_HEADERS)
    assert response.status_code == 404


def test_api_422_negative_spend(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _install_scenario_mocks(monkeypatch)
    mock_client = MagicMock()
    mock_client.table.side_effect = db.table
    monkeypatch.setattr(scenario_store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(
        "api.routes.scenarios.get_product_by_id",
        lambda pid, token: BASELINE_PRODUCT if pid == 1 else None,
    )

    create_resp = client.post(
        "/api/products/1/scenarios",
        headers=AUTH_HEADERS,
        json={"name": "Negative spend test"},
    )
    scenario_id = create_resp.json()["scenario_id"]
    item_id = next(iter(db.scenario_items))

    response = client.patch(
        f"/api/scenarios/{scenario_id}/line-items/{item_id}",
        headers=AUTH_HEADERS,
        json={"spend_usd": -1},
    )
    assert response.status_code == 422


def test_chat_skill_create_scenario(monkeypatch: pytest.MonkeyPatch) -> None:
    db = _install_scenario_mocks(monkeypatch)
    mock_client = MagicMock()
    mock_client.table.side_effect = db.table
    monkeypatch.setattr(scenario_store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(scenario_store_module, "lookup_ef", _fake_lookup_ef)
    monkeypatch.setattr(
        "api.skills.analysis.get_product_by_id",
        lambda pid, token: BASELINE_PRODUCT if pid == 1 else None,
    )
    monkeypatch.setattr(
        "api.skills.analysis.find_line_item_for_engagement",
        lambda product_name, component, material, access_token: {
            "product_id": 1,
            "version": 1,
            "item_id": 10,
            "matches": [BASELINE_PRODUCT["line_items"][0]],
        },
    )

    result = asyncio.run(
        analysis_skill.run(
            action="create_scenario",
            access_token=TEST_ACCESS_TOKEN,
            user_id=TEST_USER_ID,
            product_id=1,
            new_material="recycled aluminium",
            component="body",
            material="aluminium",
        )
    )

    assert result["success"] is True
    assert result["data"]["scenario_id"] == 1
    assert result["data"]["delta_kg"] != 0
    edited = next(li for li in db.scenario_items.values() if li["is_edited"])
    assert edited["material"] == "recycled aluminium"
    assert edited["ef_source"]
