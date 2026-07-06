"""Load + validate the dated obligation ruleset, and evaluate its conditions.

The condition language is deliberately tiny and declarative (all / any / not /
{field, op, value}) so rules stay reviewable DATA. Evaluation is THREE-VALUED:
a leaf over a missing (None) profile field returns UNKNOWN, which propagates so
that an obligation whose trigger cannot be determined is reported `uncertain`
rather than silently `no`. This is the honesty property from the Epic C plan.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Optional

import yaml

_RULES_DIR = Path(__file__).parent / "data" / "obligation_rules"

# Three-valued logic: True / False / None(=unknown).
Ternary = Optional[bool]

_LEAF_OPS = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "intersects", "nonempty"}


class RulesetError(ValueError):
    """Raised when a ruleset file is missing or structurally invalid."""


@functools.lru_cache(maxsize=8)
def load_ruleset(version: str = "v2026-07") -> dict:
    """Load and validate a dated ruleset file. Cached per version."""
    path = _RULES_DIR / f"{version}.yaml"
    if not path.exists():
        raise RulesetError(f"Ruleset '{version}' not found at {path}")
    data = yaml.safe_load(path.read_text())
    _normalize(data)
    _validate(data, version)
    return data


def _normalize(data: object) -> None:
    """Repair YAML 1.1 gotchas: `yes`/`no` parse as booleans, but we want the
    string tokens for `applies_when_matched`."""
    if not isinstance(data, dict):
        return
    for rule in data.get("rules", []):
        awm = rule.get("applies_when_matched")
        if isinstance(awm, bool):
            rule["applies_when_matched"] = "yes" if awm else "no"


def _validate(data: object, version: str) -> None:
    if not isinstance(data, dict) or "rules" not in data:
        raise RulesetError(f"Ruleset '{version}' missing top-level 'rules'.")
    if data.get("version") != version:
        raise RulesetError(
            f"Ruleset file version '{data.get('version')}' != requested '{version}'."
        )
    for rule in data["rules"]:
        for key in ("id", "framework", "condition", "applies_when_matched"):
            if key not in rule:
                raise RulesetError(f"Rule {rule.get('id', '?')} missing '{key}'.")
        if rule["applies_when_matched"] not in ("yes", "uncertain"):
            raise RulesetError(f"Rule {rule['id']}: applies_when_matched must be yes|uncertain.")
        _validate_condition(rule["condition"], rule["id"])


def _validate_condition(cond: object, rule_id: str) -> None:
    if not isinstance(cond, dict):
        raise RulesetError(f"Rule {rule_id}: condition must be a mapping.")
    # Leaf: {field, op, value} (a flat dict with a 'field' key).
    if "field" in cond:
        if cond.get("op") not in _LEAF_OPS:
            raise RulesetError(
                f"Rule {rule_id}: leaf on '{cond['field']}' has invalid op '{cond.get('op')}'."
            )
        return
    # Combinator: exactly one of all / any / not.
    if len(cond) != 1:
        raise RulesetError(f"Rule {rule_id}: a combinator must have exactly one key.")
    ((key, val),) = cond.items()
    if key in ("all", "any"):
        if not isinstance(val, list) or not val:
            raise RulesetError(f"Rule {rule_id}: '{key}' needs a non-empty list.")
        for sub in val:
            _validate_condition(sub, rule_id)
    elif key == "not":
        _validate_condition(val, rule_id)
    else:
        raise RulesetError(f"Rule {rule_id}: unknown condition key '{key}'.")


# ---------------------------------------------------------------------------
# Three-valued evaluation
# ---------------------------------------------------------------------------


def evaluate_condition(cond: dict, profile: object) -> Ternary:
    """Evaluate a condition against a profile → True / False / None(unknown)."""
    if "all" in cond:
        return _all(evaluate_condition(sub, profile) for sub in cond["all"])
    if "any" in cond:
        return _any(evaluate_condition(sub, profile) for sub in cond["any"])
    if "not" in cond:
        return _not(evaluate_condition(cond["not"], profile))
    return _leaf(cond, profile)


def _all(results) -> Ternary:
    results = list(results)
    if any(r is False for r in results):
        return False
    if any(r is None for r in results):
        return None
    return True


def _any(results) -> Ternary:
    results = list(results)
    if any(r is True for r in results):
        return True
    if any(r is None for r in results):
        return None
    return False


def _not(result: Ternary) -> Ternary:
    return None if result is None else (not result)


def _leaf(cond: dict, profile: object) -> Ternary:
    field_name = cond["field"]
    op = cond.get("op")
    expected = cond.get("value")
    if op not in _LEAF_OPS:
        raise RulesetError(f"Unknown op '{op}' on field '{field_name}'.")

    actual = getattr(profile, field_name, None)

    # 'nonempty' and boolean/empty checks are defined even when actual is falsy.
    if op == "nonempty":
        return bool(actual)
    if op == "intersects":
        if not actual:
            return False
        have = {str(x).strip().lower() for x in actual}
        want = {str(x).strip().lower() for x in expected}
        return len(have & want) > 0
    if op == "in":
        return None if actual is None else actual in expected

    # Comparisons: a missing value is UNKNOWN (cannot assert the threshold).
    if actual is None:
        # Booleans default to False in the profile, so only numeric/None fields
        # reach here as unknown.
        return None
    if op == "eq":
        return actual == expected
    if op == "ne":
        return actual != expected
    if op == "gt":
        return actual > expected
    if op == "gte":
        return actual >= expected
    if op == "lt":
        return actual < expected
    if op == "lte":
        return actual <= expected
    raise RulesetError(f"Unhandled op '{op}'.")  # pragma: no cover
