"""Pydantic request/response DTOs for the Scope-3 module (hygiene: DTOs live in
api/models/scope3_schemas.py). Kept separate from the shared api/models/schemas
so the Scope-3 lane owns its own contract.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateInventoryRequest(BaseModel):
    reporting_year: int
    boundary_approach: str = "operational_control"


class InventoryVersionDTO(BaseModel):
    inventory_id: int
    org_id: str
    reporting_year: int
    boundary_approach: str
    status: str
    is_base_year: bool
    total_kg_co2e: float | None = None
    version: int
    created_at: str | None = None
    locked_at: str | None = None


class SpendImportResponse(BaseModel):
    inventory_id: int
    parsed_rows: int
    flagged_rows: int
    file_errors: list[str] = Field(default_factory=list)


class ClassifyResponse(BaseModel):
    inventory_id: int
    classified: int
    flagged_for_review: int


class CategoryResultDTO(BaseModel):
    scope3_category: int
    method: str
    total_kg_co2e: float
    line_count: int
    notes: str | None = None


class InventoryDetailDTO(BaseModel):
    version: InventoryVersionDTO
    categories: list[CategoryResultDTO] = Field(default_factory=list)
