"""Obligation engine (Epic C, units P.1.1.b/.c).

Evaluate an ObligationProfile against a dated ruleset → a ranked set of
obligations (applicable / uncertain / not-applicable) plus a due-date timeline.
Pure logic: no DB, no network, deterministic. Every result records the
`ruleset_version` used, and moving/in-flux items stay honest (`uncertain` /
`confidence: partial`) rather than asserting fixed values.
"""

from __future__ import annotations

import datetime as _dt

from obligations.models import DueItem, EvaluationResult, Obligation, ObligationProfile
from obligations.ruleset import evaluate_condition, load_ruleset


def evaluate(profile: ObligationProfile, version: str = "v2026-07") -> EvaluationResult:
    """Diagnose which drivers bite for `profile` under ruleset `version`."""
    ruleset = load_ruleset(version)
    result = EvaluationResult(ruleset_version=version)

    for rule in ruleset["rules"]:
        obligation = _evaluate_rule(rule, profile, version)
        if obligation.applies == "yes":
            result.applicable.append(obligation)
        elif obligation.applies == "uncertain":
            result.uncertain.append(obligation)
        else:
            result.not_applicable.append(obligation)

    result.applicable.sort(key=_rank_key)
    result.uncertain.sort(key=_rank_key)
    return result


def _evaluate_rule(rule: dict, profile: ObligationProfile, version: str) -> Obligation:
    outcome = evaluate_condition(rule["condition"], profile)

    if outcome is True:
        applies = rule["applies_when_matched"]  # yes | uncertain
        reason = rule["threshold_detail"]
    elif outcome is None:
        applies = "uncertain"
        reason = "Insufficient profile data to determine the trigger — provide the missing facts."
    else:
        applies = "no"
        reason = "Threshold not met."

    return Obligation(
        rule_id=rule["id"],
        framework=rule["framework"],
        applies=applies,
        reason=reason,
        threshold_detail=rule.get("threshold_detail", ""),
        confidence=rule.get("confidence", "confirmed"),
        status=rule.get("status", "in_force"),
        due=[_due_item(d) for d in rule.get("due", [])],
        assurance=rule.get("assurance"),
        citation=rule.get("citation", ""),
        priority=int(rule.get("priority", 0)),
        ruleset_version=version,
    )


def _due_item(raw: dict) -> DueItem:
    return DueItem(what=raw["what"], date=_iso(raw.get("date")), note=raw.get("note"))


def _iso(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (_dt.date, _dt.datetime)):
        return value.isoformat()[:10]
    return str(value)


def _rank_key(o: Obligation) -> tuple:
    """Higher priority first; then earliest dated due; undated last."""
    dated = [d.date for d in o.due if d.date]
    earliest = min(dated) if dated else "9999-12-31"
    return (-o.priority, earliest)
