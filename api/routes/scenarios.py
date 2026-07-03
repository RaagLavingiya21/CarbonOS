"""FastAPI routes for scenario modeling (what-if footprint comparisons)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import CurrentUser, get_current_user
from api.models.schemas import (
    CreateScenarioRequest,
    CreateScenarioResponse,
    EditScenarioLineItemRequest,
    EditScenarioLineItemResponse,
    ScenarioDetailDTO,
    ScenarioLineItemDTO,
    ScenarioSummaryDTO,
)
from db.reader import get_product_by_id
from db.scenario_store import (
    create_scenario_from_product,
    delete_scenario,
    edit_scenario_line_item,
    get_scenario,
    list_scenarios_for_product,
)

router = APIRouter(tags=["scenarios"])


@router.post(
    "/api/products/{product_id}/scenarios",
    response_model=CreateScenarioResponse,
)
def create_scenario_route(
    product_id: int,
    request: CreateScenarioRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> CreateScenarioResponse:
    product = get_product_by_id(product_id, current_user.access_token)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")
    try:
        scenario_id = create_scenario_from_product(
            product_id,
            request.name,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CreateScenarioResponse(scenario_id=scenario_id)


@router.get(
    "/api/products/{product_id}/scenarios",
    response_model=list[ScenarioSummaryDTO],
)
def list_scenarios_route(
    product_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[ScenarioSummaryDTO]:
    product = get_product_by_id(product_id, current_user.access_token)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found.")
    scenarios = list_scenarios_for_product(product_id, current_user.access_token)
    return [ScenarioSummaryDTO.from_row(row) for row in scenarios]


@router.get("/api/scenarios/{scenario_id}", response_model=ScenarioDetailDTO)
def get_scenario_route(
    scenario_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> ScenarioDetailDTO:
    scenario = get_scenario(scenario_id, current_user.access_token)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found.")
    return ScenarioDetailDTO.from_row(scenario)


@router.patch(
    "/api/scenarios/{scenario_id}/line-items/{scenario_item_id}",
    response_model=EditScenarioLineItemResponse,
)
def edit_scenario_line_item_route(
    scenario_id: int,
    scenario_item_id: int,
    request: EditScenarioLineItemRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> EditScenarioLineItemResponse:
    scenario = get_scenario(scenario_id, current_user.access_token)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found.")
    item_ids = {int(li["scenario_item_id"]) for li in scenario.get("line_items", [])}
    if scenario_item_id not in item_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Line item {scenario_item_id} not found on scenario {scenario_id}.",
        )
    try:
        result = edit_scenario_line_item(
            scenario_item_id,
            material=request.material,
            spend_usd=request.spend_usd,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EditScenarioLineItemResponse(
        scenario_total=result["scenario_total"],
        baseline_total=result["baseline_total"],
        delta_kg=result["delta_kg"],
        delta_pct=result["delta_pct"],
        item=ScenarioLineItemDTO.from_row(result["item"]),
    )


@router.delete("/api/scenarios/{scenario_id}", status_code=204)
def delete_scenario_route(
    scenario_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    try:
        delete_scenario(
            scenario_id,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
