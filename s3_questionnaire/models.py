"""Dataclasses for the Scope-3 questionnaire framework detector (Epic B / B3).

DB-free. The persistence layer (Epic B DB phases) maps these onto the
`questionnaire_requests` / `questionnaire_questions` tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Question value types the parser infers.
NUMERIC = "numeric"
BOOLEAN = "boolean"
SELECT = "select"
NARRATIVE = "narrative"

# Frameworks the detector recognizes (plus the generic fallback).
FRAMEWORKS = ("cdp", "ecovadis", "walmart", "tesco_cdf", "generic")


@dataclass
class ParsedQuestion:
    index: int
    text: str
    question_type: str  # NUMERIC | BOOLEAN | SELECT | NARRATIVE
    framework_field_key: str | None = None  # e.g. "cdp.C6.1" for known frameworks


@dataclass
class DetectedFramework:
    framework: str  # one of FRAMEWORKS
    confidence: float  # 0–100
    is_low_confidence: bool
    matched_signals: list[str] = field(default_factory=list)


@dataclass
class ParsedQuestionnaire:
    detected: DetectedFramework
    questions: list[ParsedQuestion] = field(default_factory=list)
