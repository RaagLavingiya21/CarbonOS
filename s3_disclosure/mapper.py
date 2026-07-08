"""Disclosure datapoint mapping (Epic G / unit P.4.1.a).

Maps the Scope-3 corporate inventory onto a framework's Scope-3 datapoints
(ESRS E1 / SB253 / IFRS S2). Trust rules (plan §1), pure logic, DB-free:
  - Numbers are LOOKED UP from the inventory (kg→tCO2e), never generated; every
    numeric datapoint carries a source_ref; a missing input is flagged, not faked.
  - Formats are versioned DATA (s3_disclosure/data/frameworks.yaml); each result
    records its format_version.
  - SB253 Scope 3 output is emitted `is_provisional=True` (CARB format not final).
"""

from __future__ import annotations

import functools
from pathlib import Path

import yaml

from s3_disclosure.models import DisclosureDatapoint, DisclosureResult

_SPEC_PATH = Path(__file__).parent / "data" / "frameworks.yaml"

_CAT_NAMES = {
    1: "Purchased goods & services",
    2: "Capital goods",
    3: "Fuel- & energy-related",
    4: "Upstream transportation",
    5: "Waste generated in operations",
    6: "Business travel",
    7: "Employee commuting",
    8: "Upstream leased assets",
    9: "Downstream transportation",
    10: "Processing of sold products",
    11: "Use of sold products",
    12: "End-of-life treatment",
    13: "Downstream leased assets",
    14: "Franchises",
    15: "Investments",
}

_METHODOLOGY = (
    "Screening-grade, spend-based Scope 3 inventory using EEIO factors "
    "(Open CEDA 2025, kg CO2e per USD), prepared per the GHG Protocol Corporate "
    "Value Chain (Scope 3) Standard. Data quality: secondary/estimated, with "
    "hotspot categories deepened where supplier-specific data exists."
)


class DisclosureSpecError(ValueError):
    pass


@functools.lru_cache(maxsize=1)
def _all_specs() -> dict:
    data = yaml.safe_load(_SPEC_PATH.read_text())
    if not isinstance(data, dict) or "frameworks" not in data:
        raise DisclosureSpecError("frameworks.yaml missing 'frameworks'.")
    return data["frameworks"]


def available_frameworks() -> list[str]:
    return sorted(_all_specs())


def _t(kg: float | None) -> float | None:
    """kg CO2e → tCO2e (disclosure unit), rounded."""
    return None if kg is None else round(kg / 1000.0, 3)


def map_disclosure(inventory: dict, framework: str) -> DisclosureResult:
    """Map an inventory ({'total': kg, 'categories': {cat: kg}}) to a framework."""
    specs = _all_specs()
    if framework not in specs:
        raise DisclosureSpecError(
            f"Unknown framework '{framework}' (have {available_frameworks()})."
        )
    spec = specs[framework]
    unit = spec["unit"]
    total_kg = inventory.get("total")
    categories: dict[int, float] = inventory.get("categories") or {}

    datapoints = [_derive(dp, total_kg, categories, unit) for dp in spec["datapoints"]]

    breakdown: list[DisclosureDatapoint] = []
    if spec.get("include_category_breakdown"):
        for cat in sorted(categories):
            breakdown.append(
                DisclosureDatapoint(
                    key=f"scope3_cat{cat}",
                    label=_CAT_NAMES.get(cat, f"Category {cat}"),
                    value=_t(categories[cat]),
                    text=None,
                    unit=unit,
                    source_ref=f"Scope 3 corporate inventory (inventory:cat{cat}.total)",
                )
            )

    notes: list[str] = []
    if spec["is_provisional"]:
        notes.append(
            "PROVISIONAL: the CARB SB 253 Scope 3 report format is not final "
            "(~end-2026). This is a draft, not a filed format."
        )

    return DisclosureResult(
        framework=spec["framework"],
        format_version=spec["version"],
        is_provisional=spec["is_provisional"],
        datapoints=datapoints,
        category_breakdown=breakdown,
        notes=notes,
    )


def _derive(
    dp: dict, total_kg: float | None, categories: dict[int, float], unit: str
) -> DisclosureDatapoint:
    derive = dp["derive"]
    if derive == "methodology":
        return DisclosureDatapoint(
            key=dp["key"],
            label=dp["label"],
            value=None,
            text=_METHODOLOGY,
            unit="text",
            source_ref=None,
        )
    if derive == "scope3_total":
        val = _t(total_kg)
        return DisclosureDatapoint(
            key=dp["key"],
            label=dp["label"],
            value=val,
            text=None,
            unit=unit,
            source_ref="Scope 3 corporate inventory (inventory:total)",
            flag="ok" if val is not None else "missing",
        )
    if derive.startswith("scope3_category:"):
        cat = int(derive.split(":", 1)[1])
        val = _t(categories.get(cat))
        return DisclosureDatapoint(
            key=dp["key"],
            label=dp["label"],
            value=val,
            text=None,
            unit=unit,
            source_ref=f"Scope 3 corporate inventory (inventory:cat{cat}.total)",
            flag="ok" if val is not None else "missing",
        )
    raise DisclosureSpecError(f"Unknown derive '{derive}' for datapoint {dp['key']}.")
