"""LLM-as-judge evals for advisor chat and supplier email quality.

Scores outputs against rubrics grounded in CLAUDE.md decision rules and prompt constraints.
Live evals require ANTHROPIC_API_KEY and a built RAG index (for email drafts).

Usage:
    python -m evals.llm_judge                  # run all live evals
    python -m evals.llm_judge --skip-without-key  # skip when key absent (CI-safe)
    pytest evals/test_llm_judge.py -m llm      # run via pytest marker
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anthropic
import pytest
from dotenv import load_dotenv

from copilot.draft_email import run as draft_email_run
from copilot.models import EngagementCandidate
from llm.client import ask_advisor

load_dotenv()

FIXTURES_DIR = Path(__file__).parent / "fixtures"
_JUDGE_MODEL = "claude-sonnet-4-6"
_PASS_THRESHOLD = 4  # out of 5

_ADVISOR_RUBRIC = """\
Score the advisor response on a 1-5 scale for each criterion:
1. grounded_in_context — cites product data or GHG Protocol guidance present in sources
2. no_fabrication — does not invent numbers, EFs, or standards not in context
3. no_prescriptions — avoids recommending specific suppliers, investments, or compliance actions
4. analyst_tone — clear, professional language suitable for a sustainability analyst
5. addresses_question — directly answers the user's question

Return ONLY valid JSON:
{"scores": {"grounded_in_context": N, "no_fabrication": N, "no_prescriptions": N, \
"analyst_tone": N, "addresses_question": N}, "overall_pass": true/false, "rationale": "..."}

Pass threshold: every criterion >= 4 and overall_pass true.
"""

_EMAIL_RUBRIC = """\
Score the supplier email draft on a 1-5 scale for each criterion:
1. ghg_protocol_basis — cites a specific GHG Protocol section supporting the data request
2. data_fields_requested — asks for activity data, EF/PCF, methodology, and system boundary
3. deadline — includes a 14-day response deadline
4. professional_tone — concise, supplier-friendly, no unnecessary jargon
5. contact_aware — greeting and recipient details are appropriate for the contact info provided

Return ONLY valid JSON:
{"scores": {"ghg_protocol_basis": N, "data_fields_requested": N, "deadline": N, \
"professional_tone": N, "contact_aware": N}, "overall_pass": true/false, "rationale": "..."}

Pass threshold: every criterion >= 4 and overall_pass true.
"""


@dataclass
class JudgeResult:
    case_id: str
    eval_type: str
    passed: bool
    scores: dict[str, int]
    rationale: str
    output_preview: str


def _load_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_judge_response(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Judge returned no JSON: {text[:200]}")
    return json.loads(match.group(0))


def _judge_output(
    eval_type: str,
    case: dict[str, Any],
    output_text: str,
    client: anthropic.Anthropic,
) -> JudgeResult:
    rubric = _ADVISOR_RUBRIC if eval_type == "advisor" else _EMAIL_RUBRIC
    case_inputs = {k: v for k, v in case.items() if k != "min_score"}
    user_content = (
        f"Case ID: {case['id']}\n\n"
        f"Generated output:\n{output_text}\n\n"
        f"Original inputs:\n{json.dumps(case_inputs, indent=2)}"
    )
    response = client.messages.create(
        model=_JUDGE_MODEL,
        max_tokens=500,
        system=rubric,
        messages=[{"role": "user", "content": user_content}],
    )
    parsed = _parse_judge_response(response.content[0].text if response.content else "")
    scores = parsed.get("scores", {})
    min_score = case.get("min_score", _PASS_THRESHOLD)
    passed = parsed.get("overall_pass", False) and all(
        v >= min_score for v in scores.values()
    )
    return JudgeResult(
        case_id=case["id"],
        eval_type=eval_type,
        passed=passed,
        scores=scores,
        rationale=parsed.get("rationale", ""),
        output_preview=output_text[:300],
    )


def run_advisor_eval(case: dict[str, Any], client: anthropic.Anthropic) -> JudgeResult:
    response = ask_advisor(
        user_message=case["user_message"],
        conversation_history=case.get("conversation_history", []),
        db_context=case["db_context"],
        session_id=f"eval-advisor-{case['id']}",
    )
    if response.error:
        return JudgeResult(
            case_id=case["id"],
            eval_type="advisor",
            passed=False,
            scores={},
            rationale=f"Advisor error: {response.error}",
            output_preview="",
        )
    return _judge_output("advisor", case, response.content, client)


def run_email_eval(case: dict[str, Any], client: anthropic.Anthropic) -> JudgeResult:
    candidate = EngagementCandidate(**case["candidate"])
    result = draft_email_run(
        candidate=candidate,
        product_name=case["product_name"],
        session_id=f"eval-email-{case['id']}",
    )
    if result.error or result.draft is None:
        return JudgeResult(
            case_id=case["id"],
            eval_type="email",
            passed=False,
            scores={},
            rationale=f"Email draft error: {result.error}",
            output_preview="",
        )
    draft = result.draft
    output_text = (
        f"To: {draft.to}\nSubject: {draft.subject}\n\n{draft.body}\n\n"
        f"GHG Protocol basis: {draft.ghg_protocol_basis}\n"
        f"Citations: {result.citations}"
    )
    return _judge_output("email", case, output_text, client)


def run_all_judge_evals() -> list[JudgeResult]:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set — cannot run live LLM judge evals.")

    client = anthropic.Anthropic()
    results: list[JudgeResult] = []

    for case in _load_json(FIXTURES_DIR / "advisor_cases.json"):
        results.append(run_advisor_eval(case, client))

    for case in _load_json(FIXTURES_DIR / "email_cases.json"):
        results.append(run_email_eval(case, client))

    return results


def _print_results(results: list[JudgeResult]) -> int:
    failures = 0
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.eval_type}/{r.case_id}: {r.scores}")
        if not r.passed:
            failures += 1
            print(f"  Rationale: {r.rationale}")
    print(f"\n{len(results) - failures}/{len(results)} evals passed")
    return failures


# ---------------------------------------------------------------------------
# Pytest integration (opt-in via marker)
# ---------------------------------------------------------------------------


def _has_api_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


@pytest.mark.llm
@pytest.mark.skipif(not _has_api_key(), reason="ANTHROPIC_API_KEY not set")
def test_advisor_llm_judge_cases() -> None:
    client = anthropic.Anthropic()
    for case in _load_json(FIXTURES_DIR / "advisor_cases.json"):
        result = run_advisor_eval(case, client)
        assert result.passed, f"{case['id']} failed: {result.rationale}"


@pytest.mark.llm
@pytest.mark.skipif(not _has_api_key(), reason="ANTHROPIC_API_KEY not set")
def test_email_llm_judge_cases() -> None:
    client = anthropic.Anthropic()
    for case in _load_json(FIXTURES_DIR / "email_cases.json"):
        result = run_email_eval(case, client)
        assert result.passed, f"{case['id']} failed: {result.rationale}"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run LLM-as-judge quality evals")
    parser.add_argument(
        "--skip-without-key",
        action="store_true",
        help="Exit 0 with a skip message when ANTHROPIC_API_KEY is absent (CI-safe).",
    )
    args = parser.parse_args(argv)

    if not _has_api_key():
        if args.skip_without_key:
            print("Skipping LLM judge evals: ANTHROPIC_API_KEY not set.")
            return 0
        print("ANTHROPIC_API_KEY not set. Use --skip-without-key for CI.", file=sys.stderr)
        return 0

    results = run_all_judge_evals()
    return _print_results(results)


if __name__ == "__main__":
    sys.exit(main())
