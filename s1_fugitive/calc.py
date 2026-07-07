"""Fugitive refrigerant-leak calculations (pure).

`compute_leaked_kg` estimates the annual leaked mass by the chosen method;
`fugitive_tco2e` converts a leaked mass to tCO2e via the refrigerant GWP at a
given AR version. Mass is what gets stored; tCO2e is derived at reporting time.
"""

from __future__ import annotations

from dataclasses import dataclass

from s1_fugitive.refrigerants import refrigerant_gwp

METHODS = ("screening", "material_balance")


@dataclass(frozen=True)
class FugitiveResult:
    refrigerant: str
    method: str
    leaked_kg: float


def _req(name: str, value: float | None) -> float:
    if value is None:
        raise ValueError(f"'{name}' is required for this method.")
    if value < 0:
        raise ValueError(f"'{name}' must be non-negative.")
    return float(value)


def compute_leaked_kg(
    method: str,
    *,
    charge_kg: float | None = None,
    leak_rate_pct: float | None = None,
    purchases_kg: float | None = None,
    beginning_inventory_kg: float | None = None,
    ending_inventory_kg: float | None = None,
) -> float:
    """Leaked refrigerant mass (kg) for the period, by method.

    - screening: charge x leak_rate% (IPCC screening / simplified).
    - material_balance: purchases + beginning stock - ending stock. Clamped at 0
      (a negative result means net stock grew — no emission to report).
    """
    if method == "screening":
        return _req("charge_kg", charge_kg) * _req("leak_rate_pct", leak_rate_pct) / 100.0
    if method == "material_balance":
        leaked = (
            _req("purchases_kg", purchases_kg)
            + _req("beginning_inventory_kg", beginning_inventory_kg)
            - _req("ending_inventory_kg", ending_inventory_kg)
        )
        return max(0.0, leaked)
    raise ValueError(f"Unknown method '{method}'. Use one of {METHODS}.")


def fugitive_tco2e(leaked_kg: float, refrigerant: str, ar_version: str) -> float:
    """tCO2e = leaked_kg x GWP(refrigerant, ar_version) / 1000 (kg -> tonne)."""
    return leaked_kg * refrigerant_gwp(refrigerant, ar_version) / 1000.0
