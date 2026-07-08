"""DB-free tests for the Epic I levers/MAC route helpers."""

from __future__ import annotations

from dataclasses import asdict

from api.models.scope3_schemas import LeverDTO, MacPointDTO
from api.routes.scope3_levers import _lever_dto
from s3_levers.library import match_levers
from s3_levers.mac import build_mac_curve


def test_lever_dto_conversion():
    lev = match_levers({1})[0]
    dto = _lever_dto(lev)
    assert isinstance(dto, LeverDTO)
    assert dto.lever_id == lev.lever_id and dto.category == 1


def test_mac_points_serialize_to_dto():
    totals = {1: 700.0, 4: 120.0}
    levers = match_levers(set(totals))
    points = build_mac_curve(levers, totals)
    dtos = [MacPointDTO(**asdict(p)) for p in points]
    assert dtos and all(isinstance(d, MacPointDTO) for d in dtos)
    costs = [d.cost_per_tco2e for d in dtos]
    assert costs == sorted(costs)  # cheapest first


def test_category_parsing_shape():
    # mirrors the route's "1,4,11" -> {1,4,11}
    cats = {int(c) for c in "1,4,11".split(",") if c.strip().isdigit()}
    assert cats == {1, 4, 11}
    assert {lev.category for lev in match_levers(cats)} <= cats
