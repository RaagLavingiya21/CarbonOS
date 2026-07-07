"""Consumer decarbonization lever library (Epic I / P.3.5.a). Pure, DB-free.

Loads the curated lever data and matches levers to a company's hotspot
categories (and optionally its sub-sector). Abatement/cost values are ROUGH
estimates — labelled as such wherever surfaced.
"""

from __future__ import annotations

import functools
from pathlib import Path

import yaml

from s3_levers.models import Lever

_LEVERS_PATH = Path(__file__).parent / "data" / "levers.yaml"


@functools.lru_cache(maxsize=1)
def load_levers() -> list[Lever]:
    data = yaml.safe_load(_LEVERS_PATH.read_text())
    return [
        Lever(
            lever_id=x["id"],
            name=x["name"],
            category=int(x["category"]),
            abatement_pct=float(x["abatement_pct"]),
            cost_per_tco2e=float(x["cost_per_tco2e"]),
            applicability=[str(a).lower() for a in x.get("applicability", ["all"])],
            source=x.get("source", ""),
        )
        for x in data["levers"]
    ]


def match_levers(categories: set[int], sub_sector: str | None = None) -> list[Lever]:
    """Levers targeting the given hotspot categories, filtered by sub-sector.

    A lever applies when its category is in `categories` AND its applicability
    is "all" or includes the sub-sector (or no sub-sector is given).
    """
    sub = (sub_sector or "").strip().lower()
    out: list[Lever] = []
    for lev in load_levers():
        if lev.category not in categories:
            continue
        if sub and "all" not in lev.applicability and sub not in lev.applicability:
            continue
        out.append(lev)
    return sorted(out, key=lambda x: (x.category, x.lever_id))
