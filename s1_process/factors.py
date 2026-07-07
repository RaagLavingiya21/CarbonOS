"""Process emission-factor library (IPCC 2006 GL default factors).

One dominant gas per process (the MVP model — add a second record for a
secondary gas). Factors are expressed as kg of gas per unit of activity, and
carry the activity unit + source so intake can prefill and cite them. Values are
IPCC defaults; an org can always use the `custom` process to supply its own.

Never store CO2e — these produce a gas mass, converted to CO2e at reporting time.
"""

from __future__ import annotations

# Canonical gas-species names — MUST match s1_calc.gwp.GWP_100 keys.
PROCESS_GASES = ("Carbon dioxide", "Methane", "Nitrous oxide")


class UnknownProcess(Exception):
    """Raised when a process type is not in the library."""


# process_type -> factor. value is kg gas / activity_unit.
PROCESS_FACTORS: dict[str, dict] = {
    "cement_clinker": {
        "label": "Cement (clinker)", "gas": "Carbon dioxide",
        "value": 510.0, "unit": "kg CO2/t clinker", "activity_unit": "t clinker",
        "source": "IPCC 2006 GL v3 Ch.2 (clinker calcination, ~0.51 t/t)",
    },
    "lime": {
        "label": "Lime", "gas": "Carbon dioxide",
        "value": 750.0, "unit": "kg CO2/t lime", "activity_unit": "t lime",
        "source": "IPCC 2006 GL v3 Ch.2 (high-calcium lime)",
    },
    "glass": {
        "label": "Glass", "gas": "Carbon dioxide",
        "value": 200.0, "unit": "kg CO2/t glass", "activity_unit": "t glass",
        "source": "IPCC 2006 GL v3 Ch.2 (carbonate decomposition)",
    },
    "soda_ash_use": {
        "label": "Soda ash (use)", "gas": "Carbon dioxide",
        "value": 415.0, "unit": "kg CO2/t soda ash", "activity_unit": "t soda ash",
        "source": "IPCC 2006 GL v3 Ch.3 (0.415 t/t)",
    },
    "ammonia": {
        "label": "Ammonia", "gas": "Carbon dioxide",
        "value": 1694.0, "unit": "kg CO2/t NH3", "activity_unit": "t NH3",
        "source": "IPCC 2006 GL v3 Ch.3 (conventional reforming, no capture)",
    },
    "nitric_acid": {
        "label": "Nitric acid", "gas": "Nitrous oxide",
        "value": 9.0, "unit": "kg N2O/t HNO3", "activity_unit": "t HNO3",
        "source": "IPCC 2006 GL v3 Ch.3 (uncontrolled high-pressure)",
    },
    "adipic_acid": {
        "label": "Adipic acid", "gas": "Nitrous oxide",
        "value": 264.0, "unit": "kg N2O/t adipic acid", "activity_unit": "t adipic acid",
        "source": "IPCC 2006 GL v3 Ch.3 (uncontrolled)",
    },
}


def get_process_factor(process_type: str) -> dict:
    try:
        return PROCESS_FACTORS[process_type]
    except KeyError as exc:
        raise UnknownProcess(f"Unknown process type: {process_type}") from exc


def list_process_factors() -> list[dict]:
    return [{"process_type": k, **v} for k, v in PROCESS_FACTORS.items()]
