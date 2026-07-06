"""Framework detection + question parsing (Epic B / unit P.4.2.1) — the second
🔴 make-or-break classifier.

Given the text of an inbound questionnaire, decide which framework it is
(CDP / EcoVadis / Walmart / Tesco-CDF / generic) and parse it into a structured
question set with inferred value types. Deterministic, DB-free, no LLM — so it
runs in CI and the eval can measure accuracy before any UI is built (same
discipline as the A3 spend classifier).

Trust property (mirrors A3): the detector must NOT confidently mis-label. When
the signal is weak/ambiguous it returns `generic` or flags `is_low_confidence`,
so the wrong per-framework template is never silently applied downstream.
"""

from __future__ import annotations

import re

from s3_questionnaire.models import (
    BOOLEAN,
    NARRATIVE,
    NUMERIC,
    SELECT,
    DetectedFramework,
    ParsedQuestion,
    ParsedQuestionnaire,
)

_CONFIDENT = 60.0  # >= this is a confident framework call
_MIN_FRAMEWORK = 40.0  # below this we fall back to generic

# Per-framework signature signals: (compiled regex, weight, label). A framework
# NAME is a strong signal (50); structural markers add corroboration (15–20).
_Signal = tuple[re.Pattern[str], float, str]


def _sig(pattern: str, weight: float, label: str) -> _Signal:
    return (re.compile(pattern, re.I), weight, label)


_SIGNALS: dict[str, list[_Signal]] = {
    "cdp": [
        _sig(r"\bCDP\b", 50, "CDP name"),
        _sig(r"\bC[0-9]{1,2}\.[0-9]{1,2}\b", 25, "CDP question numbering (C6.1)"),
        _sig(r"climate change (questionnaire|20\d\d)", 20, "CDP climate questionnaire"),
        _sig(r"\bgross global scope\b", 15, "CDP scope phrasing"),
    ],
    "ecovadis": [
        _sig(r"\becovadis\b", 50, "EcoVadis name"),
        _sig(r"sustainable procurement", 20, "EcoVadis theme"),
        _sig(r"labor (&|and) human rights", 20, "EcoVadis theme"),
        _sig(r"\b(environment|ethics) theme\b", 15, "EcoVadis theme label"),
    ],
    "walmart": [
        _sig(r"\bproject gigaton\b|\bgigaton\b", 50, "Gigaton"),
        _sig(r"\bTHESIS\b", 25, "THESIS index"),
        _sig(r"sustainability index", 20, "Walmart index"),
        _sig(r"\bgiga guru\b", 20, "Giga Guru"),
    ],
    "tesco_cdf": [
        _sig(r"common data framework", 50, "Common Data Framework"),
        _sig(r"\btesco\b", 35, "Tesco name"),
        _sig(r"\b(foundational|expanded|granular)\b", 20, "CDF tier"),
    ],
}


def detect_framework(text: str) -> DetectedFramework:
    """Score each framework's signals against the text; pick the best, or fall
    back to `generic` when the signal is weak."""
    text = text or ""
    scores: dict[str, float] = {}
    matched: dict[str, list[str]] = {}
    for framework, signals in _SIGNALS.items():
        score = 0.0
        labels: list[str] = []
        for pattern, weight, label in signals:
            if pattern.search(text):
                score += weight
                labels.append(label)
        scores[framework] = min(score, 100.0)
        matched[framework] = labels

    best = max(scores, key=lambda f: scores[f]) if scores else "generic"
    best_score = scores.get(best, 0.0)

    if best_score < _MIN_FRAMEWORK:
        return DetectedFramework(
            framework="generic",
            confidence=round(best_score, 1),
            is_low_confidence=True,
            matched_signals=[],
        )
    return DetectedFramework(
        framework=best,
        confidence=round(best_score, 1),
        is_low_confidence=best_score < _CONFIDENT,
        matched_signals=matched[best],
    )


# --- question parsing -------------------------------------------------------

_NUMERIC_CUES = re.compile(
    r"\b(kg\s*co2e?|tco2e?|tonnes?|metric tons?|kwh|mwh|percent|%|how much|"
    r"what (was|were|is) your (total|gross)|total .* emissions|number of)\b",
    re.I,
)
_BOOLEAN_CUES = re.compile(r"\byes\s*/?\s*no\b|^\s*(do|does|have|has|is|are)\b", re.I)
_SELECT_CUES = re.compile(r"\bselect\b|choose|which of the following|\bdropdown\b", re.I)

# A line is treated as a question if it is numbered, ends with '?', or is a
# directive (describe/provide/select/…).
_LOOKS_LIKE_QUESTION = re.compile(
    r"\?\s*$|^\s*(C[0-9]{1,2}\.[0-9]{1,2}|Q?[0-9]{1,2}[.)])|"
    r"\b(describe|provide|please|select|what|how|do you|have you|list|explain)\b",
    re.I,
)
_FIELD_KEY = re.compile(r"\b(C[0-9]{1,2}\.[0-9]{1,2})\b")


def infer_question_type(text: str) -> str:
    if _SELECT_CUES.search(text):
        return SELECT
    if _NUMERIC_CUES.search(text):
        return NUMERIC
    if _BOOLEAN_CUES.search(text):
        return BOOLEAN
    return NARRATIVE


def parse_questions(text: str, framework: str) -> list[ParsedQuestion]:
    """Split questionnaire text into typed questions. For frameworks with
    embedded IDs (e.g. CDP 'C6.1') the id becomes the field key."""
    questions: list[ParsedQuestion] = []
    idx = 0
    for raw in (text or "").splitlines():
        line = raw.strip()
        if len(line) < 8 or not _LOOKS_LIKE_QUESTION.search(line):
            continue
        field_key = None
        m = _FIELD_KEY.search(line)
        if m and framework == "cdp":
            field_key = f"cdp.{m.group(1)}"
        questions.append(
            ParsedQuestion(
                index=idx,
                text=line,
                question_type=infer_question_type(line),
                framework_field_key=field_key,
            )
        )
        idx += 1
    return questions


def parse_questionnaire(text: str) -> ParsedQuestionnaire:
    """Detect the framework and parse the question set in one call."""
    detected = detect_framework(text)
    questions = parse_questions(text, detected.framework)
    return ParsedQuestionnaire(detected=detected, questions=questions)
