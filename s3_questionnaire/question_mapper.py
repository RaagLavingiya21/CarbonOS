"""Question → datapoint mapping (Epic B / unit P.4.2.2) — the third 🔴 classifier
and the trust-critical join.

Maps a parsed questionnaire question to a datapoint in the corporate inventory
(Epic A) so an answer can be drafted. The NON-NEGOTIABLE rule (plan §1):

    Numbers are LOOKED UP, never generated. A numeric answer resolves to a
    specific inventory datapoint (a category total or the Scope 3 total). If it
    cannot be mapped, it is flagged `needs_human` — never fabricated. Non-numeric
    questions (boolean/select/narrative) are not auto-numbered; they are left for
    the analyst.

Pure logic, DB-free, deterministic. The route supplies the inventory datapoints
(from db.s3_inventory_store); this module never touches the DB or an LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from s3_questionnaire.models import NUMERIC, ParsedQuestion

# Category keyword → Scope 3 category number (subset that questionnaires ask for).
_CATEGORY_KEYWORDS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"purchased goods|raw materials|ingredients|category 1\b", re.I), 1),
    (re.compile(r"capital goods|category 2\b", re.I), 2),
    (re.compile(r"fuel[- ]and[- ]energy|fuel and energy|category 3\b", re.I), 3),
    (re.compile(r"upstream transport|inbound (transport|logistics)|category 4\b", re.I), 4),
    (re.compile(r"\bwaste\b|category 5\b", re.I), 5),
    (re.compile(r"business travel|category 6\b", re.I), 6),
    (re.compile(r"employee commut|category 7\b", re.I), 7),
    (re.compile(r"use of sold|use[- ]phase|category 11\b", re.I), 11),
    (re.compile(r"end[- ]of[- ]life|category 12\b", re.I), 12),
]

# CDP field keys that mean the Scope 3 grand total.
_CDP_SCOPE3_TOTAL = re.compile(r"cdp\.C6\.(5|10)", re.I)
_SCOPE3_TOTAL_TEXT = re.compile(r"\bscope 3\b.*(total|gross|overall)|total scope 3", re.I)
_OUT_OF_SCOPE = re.compile(r"\bscope [12]\b", re.I)


@dataclass
class QuestionMapping:
    question_index: int
    datapoint_ref: str | None  # e.g. "inventory:total" | "inventory:cat1.total" | None
    mapped_value: float | None
    answer_text: str | None
    confidence_score: float  # 0–100
    method: str  # "inventory" | "unmapped"
    citation: str | None
    flag_status: str  # "ok" | "low_confidence" | "needs_human"


def map_question(question: ParsedQuestion, inventory: dict) -> QuestionMapping:
    """Map one question to an inventory datapoint.

    Args:
        question: a ParsedQuestion (from framework_detector).
        inventory: {"total": float, "categories": {cat_num: kg_co2e}} — supplied
            by the route from the locked Epic A inventory.
    """
    # Non-numeric questions are never auto-numbered — leave for the analyst.
    if question.question_type != NUMERIC:
        return _needs_human(question, "Non-numeric question — analyst provides the answer.")

    text = f"{question.framework_field_key or ''} {question.text}"

    # Scope 1/2 asked inside a Scope-3 module → cannot answer from this inventory.
    if _OUT_OF_SCOPE.search(text) and not _SCOPE3_TOTAL_TEXT.search(text):
        return _needs_human(question, "Scope 1/2 datapoint — not in the Scope 3 inventory.")

    total = inventory.get("total")
    categories: dict[int, float] = inventory.get("categories") or {}

    # 1) Scope 3 grand total (by CDP field key or text).
    if _CDP_SCOPE3_TOTAL.search(text) or _SCOPE3_TOTAL_TEXT.search(text):
        if total is None:
            return _needs_human(question, "Scope 3 total not available in the inventory.")
        return _mapped(question, "inventory:total", float(total), 95.0)

    # 2) A specific Scope 3 category.
    for pattern, cat in _CATEGORY_KEYWORDS:
        if pattern.search(text):
            value = categories.get(cat)
            if value is None:
                return _needs_human(
                    question, f"Category {cat} not present in this inventory version."
                )
            return _mapped(question, f"inventory:cat{cat}.total", float(value), 90.0)

    # 3) Numeric but unmatched → flag; NEVER fabricate a number.
    return _needs_human(question, "No inventory datapoint matched — needs human input.")


def _mapped(question: ParsedQuestion, ref: str, value: float, confidence: float) -> QuestionMapping:
    return QuestionMapping(
        question_index=question.index,
        datapoint_ref=ref,
        mapped_value=value,
        answer_text=f"{value:.0f} kg CO2e",
        confidence_score=confidence,
        method="inventory",
        citation=f"Scope 3 corporate inventory ({ref})",
        flag_status="ok" if confidence >= 80 else "low_confidence",
    )


def _needs_human(question: ParsedQuestion, reason: str) -> QuestionMapping:
    return QuestionMapping(
        question_index=question.index,
        datapoint_ref=None,
        mapped_value=None,
        answer_text=None,
        confidence_score=0.0,
        method="unmapped",
        citation=None,
        flag_status="needs_human",
    )


def map_questions(questions: list[ParsedQuestion], inventory: dict) -> list[QuestionMapping]:
    return [map_question(q, inventory) for q in questions]
