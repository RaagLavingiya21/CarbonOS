"""Activity-data unit normalization to heat input (mmBtu).

Energy units convert directly; volume/mass units (scf, Ccf, Mcf, gallons, tons)
convert via the fuel's default higher heating value (HHV). Using the HHV keeps
the Ccf->therm relationship internally consistent with the EF table's default
NG heat content (1.026e-3 mmBtu/scf => 1.026 therms/Ccf) rather than hard-coding
a separate EIA average. See research/2.1 and 2.3.
"""

from __future__ import annotations

THERM_TO_MMBTU = 0.1          # 1 therm = 0.1 mmBtu (energy)
GJ_TO_MMBTU = 0.947817        # 1 GJ = 0.947817 mmBtu
SCF_PER_CCF = 100.0           # 1 Ccf = 100 standard cubic feet
SCF_PER_MCF = 1000.0          # 1 Mcf = 1000 standard cubic feet

_DIRECT_ENERGY = {
    "mmbtu": 1.0,
    "therms": THERM_TO_MMBTU,
    "therm": THERM_TO_MMBTU,
    "gj": GJ_TO_MMBTU,
}
# Volume/mass units expressed as a multiple of the HHV's native unit (per-scf,
# per-gal, per-ton). The HHV supplies the mmBtu-per-native-unit factor.
_NATIVE_MULTIPLE = {
    "scf": 1.0,
    "ccf": SCF_PER_CCF,   # HHV is per scf
    "mcf": SCF_PER_MCF,   # HHV is per scf
    "gal": 1.0,
    "gallons": 1.0,
    "ton": 1.0,
    "tons": 1.0,
}


class UnitConversionError(ValueError):
    """Raised when an activity unit cannot be converted to mmBtu."""


def to_mmbtu(value: float, unit: str, hhv: float | None = None) -> float:
    """Convert an activity quantity to heat input in mmBtu.

    Args:
        value: activity quantity in the native unit.
        unit:  therms|mmBtu|GJ|scf|Ccf|Mcf|gal|ton (case-insensitive).
        hhv:   default higher heating value in mmBtu per native unit
               (mmBtu/scf, mmBtu/gal, mmBtu/ton) — required for volume/mass units.
    """
    u = unit.strip().lower()
    if u in _DIRECT_ENERGY:
        return value * _DIRECT_ENERGY[u]
    if u in _NATIVE_MULTIPLE:
        if hhv is None:
            raise UnitConversionError(
                f"HHV required to convert {unit} to mmBtu (volume/mass unit)."
            )
        return value * _NATIVE_MULTIPLE[u] * hhv
    raise UnitConversionError(f"Unsupported activity unit: {unit!r}")
