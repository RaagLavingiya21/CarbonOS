"""Consolidation multiplier computation (GHG Protocol Corporate Standard Ch.3).

Three approaches, one chosen per inventory and applied to every entity:
  - equity_share:        emissions x economic interest %
  - financial_control:   100% where the company has financial control; a jointly
                         controlled operation reports at equity %; else 0%.
  - operational_control: 100% where the company has authority to implement
                         operating policies; equity is irrelevant; else 0%.

See the worked 40%-JV example in research/2.2 (2.5x range across approaches ->
the approach must be immutably declared at the inventory level).
"""

from __future__ import annotations

from dataclasses import dataclass

APPROACHES = ("equity_share", "financial_control", "operational_control")

JOINTLY_CONTROLLED_TYPES = frozenset(
    {"joint_venture", "jointly_controlled_operation"}
)


@dataclass(frozen=True)
class ConsolidationResult:
    multiplier: float          # [0.0-1.0]
    rationale: str             # human-readable audit note


def compute_consolidation_multiplier(
    approach: str,
    *,
    equity_pct: float | None,
    economic_interest_pct: float | None = None,
    has_financial_control: bool = False,
    has_operational_control: bool = False,
    entity_type: str | None = None,
) -> ConsolidationResult:
    """Return the [0.0-1.0] multiplier and an audit rationale for one entity."""
    if approach not in APPROACHES:
        raise ValueError(f"Unknown consolidation approach: {approach!r}")

    interest = economic_interest_pct if economic_interest_pct is not None else equity_pct
    equity_fraction = (interest or 0.0) / 100.0
    jointly_controlled = entity_type in JOINTLY_CONTROLLED_TYPES

    if approach == "equity_share":
        return ConsolidationResult(
            multiplier=_clamp(equity_fraction),
            rationale=(
                f"Equity share: economic interest {interest or 0.0:g}% "
                f"-> multiplier {equity_fraction:.4f}."
            ),
        )

    if approach == "financial_control":
        if not has_financial_control:
            return ConsolidationResult(
                0.0, "Financial control: no financial control -> 0% consolidated."
            )
        if jointly_controlled:
            return ConsolidationResult(
                _clamp(equity_fraction),
                f"Financial control: jointly controlled operation reports at "
                f"equity {interest or 0.0:g}% -> multiplier {equity_fraction:.4f}.",
            )
        return ConsolidationResult(
            1.0, "Financial control: company has financial control -> 100% consolidated."
        )

    # operational_control
    if has_operational_control:
        return ConsolidationResult(
            1.0,
            "Operational control: company has authority to implement operating "
            "policies -> 100% consolidated (equity irrelevant).",
        )
    return ConsolidationResult(
        0.0, "Operational control: no operational control -> 0% consolidated."
    )


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
