"""Business-case / why-now builder (Epic C / unit P.1.1.d).

Turns an EvaluationResult (+ optional cascade signals) into a STRUCTURED,
deterministic "why now" — headline, primary driver, nearest deadline, what's at
stake, and watch-items. No LLM: every field is derived from the engine output,
so dates and obligations are never invented (an optional narrative layer can
phrase this later, but the facts come from here). DB-free and testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from s3_obligations.cascade import CascadeSignal
from s3_obligations.models import EvaluationResult


@dataclass
class BusinessCase:
    headline: str
    primary_driver: str | None  # framework of the top-ranked applicable obligation
    applicable_count: int
    uncertain_count: int
    nearest_deadline: tuple[str, str, str] | None  # (date, framework, what)
    at_stake: list[str] = field(default_factory=list)
    watch_items: list[str] = field(default_factory=list)
    cascade_exposure: list[str] = field(default_factory=list)


# Short "what's at stake" lines per framework, used when that framework applies.
_AT_STAKE: dict[str, str] = {
    "California SB 253": "Annual GHG report incl. Scope 3 from 2027; assurance phases in.",
    "CSRD / ESRS E1": "Mandatory ESRS E1 disclosure: Scope 3 + value-chain data, iXBRL tagging.",
    "IFRS S2 / ISSB": "Scope 3 disclosure per GHG Protocol in an ISSB-adopting jurisdiction.",
    "SBTi Corporate Net-Zero Standard V2.0": (
        "Category A: Scope 3 targets are mandatory and base-year limited assurance is required."
    ),
    "Customer / retailer data request": (
        "Contract-linked questionnaire — answering it is needed to keep/win the account."
    ),
}


def build_business_case(
    result: EvaluationResult, cascade: list[CascadeSignal] | None = None
) -> BusinessCase:
    """Assemble the deterministic why-now case from engine output."""
    applicable = result.applicable
    uncertain = result.uncertain
    timeline = result.timeline
    nearest = timeline[0] if timeline else None
    primary = applicable[0].framework if applicable else None

    at_stake = [_AT_STAKE.get(o.framework, o.threshold_detail) for o in applicable]
    watch_items = [f"{o.framework}: {_watch_reason(o)}" for o in uncertain]
    cascade_lines = [
        f"{s.customer} → {s.matched_buyer} ({', '.join(s.regimes)}) will cascade a Scope 3 request"
        for s in (cascade or [])
    ]

    headline = _headline(applicable, uncertain, nearest, cascade_lines)

    return BusinessCase(
        headline=headline,
        primary_driver=primary,
        applicable_count=len(applicable),
        uncertain_count=len(uncertain),
        nearest_deadline=nearest,
        at_stake=at_stake,
        watch_items=watch_items,
        cascade_exposure=cascade_lines,
    )


def _watch_reason(obligation) -> str:
    if obligation.status == "watch":
        return "matched, but status is unsettled (watch) — monitor."
    return obligation.reason


def _headline(applicable, uncertain, nearest, cascade_lines) -> str:
    if not applicable and not uncertain and not cascade_lines:
        return "No regulatory or customer drivers detected from the current profile."
    parts: list[str] = []
    if applicable:
        parts.append(f"{len(applicable)} driver{'s' if len(applicable) != 1 else ''} apply now")
    if uncertain:
        parts.append(f"{len(uncertain)} to watch")
    if cascade_lines:
        parts.append(f"{len(cascade_lines)} cascade exposure via customers")
    lead = "; ".join(parts)
    if nearest:
        lead += f". Nearest deadline: {nearest[0]} — {nearest[1]} ({nearest[2]})"
    return lead + "."
