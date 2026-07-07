"""Green-claims substantiation + compliance flagging (Epic I / P.4.5). Pure, DB-free.

LEGAL-SENSITIVE — this flags exposure and gates substantiation; it is NOT legal
advice, and the substantiation output is deliberately conservative (plan §1):

  - A claim is substantiable ONLY from primary-data-backed, assured figures
    (Primary Data Share ≥ threshold AND external assurance). A spend-based
    screening estimate can NEVER substantiate a public claim — it is refused
    with a reason.
  - Jurisdiction compliance flags come from a dated ruleset (EmpCo/GCD/FTC). An
    offset-based B2C neutrality claim is flagged PROHIBITED in the EU (EmpCo).
"""

from __future__ import annotations

import functools
import re
from pathlib import Path

import yaml

from s3_levers.models import ClaimAssessment, ComplianceFlag

_RULES_PATH = Path(__file__).parent / "data" / "claims_rules.yaml"
_PDS_THRESHOLD = 0.5  # ≥50% primary-data share required to substantiate


@functools.lru_cache(maxsize=1)
def _rules() -> dict:
    return yaml.safe_load(_RULES_PATH.read_text())


def assess_claim(
    claim_text: str,
    *,
    primary_data_share: float = 0.0,
    assured: bool = False,
    jurisdiction: str = "EU",
    offset_based: bool = False,
) -> ClaimAssessment:
    """Assess whether a green claim is substantiable + flag compliance exposure."""
    rules = _rules()
    text = claim_text or ""
    flags: list[ComplianceFlag] = []

    for rule in rules["rules"]:
        if rule["jurisdiction"] != jurisdiction:
            continue
        if not re.search(rule["pattern"], text, re.I):
            continue
        # A rule that only bites offset-based claims is skipped otherwise.
        if rule.get("requires_offsetting") and not offset_based:
            continue
        flags.append(
            ComplianceFlag(
                rule_id=rule["id"],
                jurisdiction=rule["jurisdiction"],
                framework=rule["framework"],
                verdict=rule["verdict"],
                note=rule["note"],
            )
        )

    prohibited = any(f.verdict == "prohibited" for f in flags)
    evidence_ok = primary_data_share >= _PDS_THRESHOLD and assured
    substantiable = evidence_ok and not prohibited

    if prohibited:
        reason = f"Prohibited in {jurisdiction} — cannot be made regardless of evidence."
    elif primary_data_share < _PDS_THRESHOLD:
        reason = (
            f"Primary Data Share {primary_data_share:.0%} < {_PDS_THRESHOLD:.0%}: a spend-based "
            "screening estimate cannot substantiate a public claim — needs primary/supplier data."
        )
    elif not assured:
        reason = "Needs external assurance of the underlying figures before public use."
    else:
        reason = "Substantiable from primary-data-backed, assured figures."

    return ClaimAssessment(
        claim_text=text,
        jurisdiction=jurisdiction,
        substantiable=substantiable,
        substantiation_reason=reason,
        ruleset_version=rules["version"],
        flags=flags,
    )
