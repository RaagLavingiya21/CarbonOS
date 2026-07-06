"""Unit normalization to a canonical energy unit (MWh) with an auditable trail.

Every ingested consumption datum is converted to MWh so the calc engine works in
one unit. Each conversion returns the factor used and a human-readable note so the
audit log (PRD 5.6) can reproduce it. The `MBtu` vs `MMBtu` ambiguity is guarded
explicitly (PRD 5.1): a bare "mbtu" is rejected rather than silently assumed.

Leaf module — imports nothing internal.
"""

from __future__ import annotations

from dataclasses import dataclass

CANONICAL_UNIT = "MWh"

# MWh per one unit of the source. Sources are matched case-insensitively.
# Steam/heat/cooling carriers (lbs steam, ton-hours) convert via a fuel/efficiency
# step handled in s2_calc, not here, so they are intentionally absent for now.
_MWH_PER_UNIT: dict[str, float] = {
    "mwh": 1.0,
    "kwh": 0.001,
    "wh": 0.000001,
    "gwh": 1000.0,
    "therm": 0.0293071,
    "therms": 0.0293071,
    "mmbtu": 0.293071,  # 1 MMBtu = 0.293071 MWh
    "dth": 0.293071,  # dekatherm == 1 MMBtu
}

# Units we refuse to convert without disambiguation, mapped to guidance.
_AMBIGUOUS: dict[str, str] = {
    "mbtu": (
        "'MBtu' is ambiguous (thousand-BTU vs. MMBtu). "
        "Re-label the source as 'MMBtu' or 'thousand_btu' before ingesting."
    ),
    "ccf": (
        "'CCF' is a gas volume, not energy; convert with a documented heat "
        "content (therms/CCF) upstream, then ingest as therms."
    ),
}


@dataclass(frozen=True)
class NormalizedQuantity:
    canonical_mwh: float
    source_quantity: float
    source_unit: str
    factor_mwh_per_unit: float
    conversion_note: str


class UnitConversionError(ValueError):
    """Raised when a source unit is unknown or ambiguous."""


def normalize_to_mwh(quantity: float, unit: str) -> NormalizedQuantity:
    """Convert `quantity` in `unit` to canonical MWh with an audit record."""
    key = unit.strip().lower()
    if key in _AMBIGUOUS:
        raise UnitConversionError(_AMBIGUOUS[key])
    if key not in _MWH_PER_UNIT:
        raise UnitConversionError(
            f"Unsupported unit '{unit}'. Supported: {sorted(_MWH_PER_UNIT)}."
        )
    factor = _MWH_PER_UNIT[key]
    canonical = quantity * factor
    note = f"{quantity} {unit} x {factor} MWh/{key} = {canonical:g} {CANONICAL_UNIT}"
    return NormalizedQuantity(
        canonical_mwh=canonical,
        source_quantity=quantity,
        source_unit=unit,
        factor_mwh_per_unit=factor,
        conversion_note=note,
    )
