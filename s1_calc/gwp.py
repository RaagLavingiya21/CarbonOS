"""Global Warming Potential layer — canonical GWP-100 values + CO2e conversion.

This is the single source of truth for GWP (the DB `s1_gwp_value` table is
seeded from GWP_100 here). GWP is applied at reporting time over stored gas
masses; it is never baked into the stored record. Switching ar_version yields a
different CO2e from identical gas masses — no mutation. AR6 splits methane into
fossil (29.8) and biogenic (27.9). See research/2.1 section 5 and 2.2 C3.
"""

from __future__ import annotations

from s1_calc.models import GasMasses

# ar_version -> species common_name -> carbon_source -> gwp_100
GWP_100: dict[str, dict[str, dict[str, float]]] = {
    "AR4": {
        "Carbon dioxide": {"all": 1.0},
        "Methane": {"all": 25.0},
        "Nitrous oxide": {"all": 298.0},
        "Sulfur hexafluoride": {"all": 22800.0},
        "Nitrogen trifluoride": {"all": 17200.0},
        "HFC-134a": {"all": 1430.0},
        "HFC-32": {"all": 675.0},
        "HFC-125": {"all": 3500.0},
        "CF4": {"all": 7390.0},
    },
    "AR5": {
        "Carbon dioxide": {"all": 1.0},
        "Methane": {"all": 28.0},
        "Nitrous oxide": {"all": 265.0},
        "Sulfur hexafluoride": {"all": 23500.0},
        "Nitrogen trifluoride": {"all": 16100.0},
        "HFC-134a": {"all": 1430.0},
        "HFC-32": {"all": 677.0},
        "HFC-125": {"all": 3170.0},
        "CF4": {"all": 6630.0},
    },
    "AR6": {
        "Carbon dioxide": {"all": 1.0},
        "Methane": {"fossil": 29.8, "biogenic": 27.9},
        "Nitrous oxide": {"all": 273.0},
        "Sulfur hexafluoride": {"all": 25200.0},
        "Nitrogen trifluoride": {"all": 17400.0},
        "HFC-134a": {"all": 1526.0},
        "HFC-32": {"all": 771.0},
        "HFC-125": {"all": 3740.0},
        "CF4": {"all": 7380.0},
    },
}


def gwp_100(species: str, ar_version: str, carbon_source: str = "all") -> float:
    """GWP-100 for a species under an assessment report.

    Falls back to 'all' when the requested carbon_source is not split, and to
    'fossil' for AR6 methane when 'all' is requested (combustion CH4 is fossil).
    """
    try:
        table = GWP_100[ar_version][species]
    except KeyError as exc:
        raise KeyError(f"No GWP for species={species!r} version={ar_version!r}") from exc
    if carbon_source in table:
        return table[carbon_source]
    if "all" in table:
        return table["all"]
    if "fossil" in table:  # AR6 CH4 with carbon_source='all' -> fossil default
        return table["fossil"]
    return next(iter(table.values()))


def to_co2e(masses: GasMasses, ar_version: str) -> float:
    """Gross Scope 1 CO2e (tonnes) from gas masses. Biogenic CO2 is EXCLUDED
    (reported separately via biogenic_co2e). CH4/N2O from biomass ARE included."""
    kg = (
        masses.kg_co2_fossil * gwp_100("Carbon dioxide", ar_version)
        + masses.kg_ch4 * gwp_100("Methane", ar_version, "fossil")
        + masses.kg_n2o * gwp_100("Nitrous oxide", ar_version)
        + masses.kg_sf6 * gwp_100("Sulfur hexafluoride", ar_version)
        + masses.kg_nf3 * gwp_100("Nitrogen trifluoride", ar_version)
    )
    return kg / 1000.0


def biogenic_co2e(masses: GasMasses, ar_version: str) -> float:
    """Biogenic CO2 as a separate memo line (tonnes) — never in the S1 total."""
    return masses.kg_co2_biogenic * gwp_100("Carbon dioxide", ar_version) / 1000.0
