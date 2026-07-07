"""Questionnaire answer export packs (Epic B / unit P.4.2.6).

Turns the reviewed question→answer set into a submittable pack (CSV or Markdown).
Dependency-free (stdlib only) and pure — the route supplies already-joined answer
rows from the DB; this module just serializes them.

Trust discipline carried into the output (plan §1): a row is only rendered with a
value when it is a real, cited answer. Anything flagged `needs_human` (or lacking
an answer) renders an explicit "⚠ NEEDS HUMAN INPUT" placeholder — a fabricated
number never reaches the exported file.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

_NEEDS_HUMAN = "⚠ NEEDS HUMAN INPUT"


@dataclass
class AnswerRow:
    question_text: str
    question_type: str
    framework_field_key: str | None
    answer_text: str | None
    datapoint_ref: str | None
    citation: str | None
    confidence_score: float
    flag_status: str  # ok | low_confidence | needs_human


def _answered(row: AnswerRow) -> bool:
    return row.flag_status != "needs_human" and bool(row.answer_text)


def _answer_cell(row: AnswerRow) -> str:
    return row.answer_text if _answered(row) else _NEEDS_HUMAN


def to_csv(answers: list[AnswerRow]) -> str:
    """Serialize to a flat CSV (one row per question)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["field_key", "question", "type", "answer", "citation", "confidence", "flag"])
    for row in answers:
        writer.writerow(
            [
                row.framework_field_key or "",
                row.question_text,
                row.question_type,
                _answer_cell(row),
                row.citation or "" if _answered(row) else "",
                f"{row.confidence_score:.0f}" if _answered(row) else "",
                row.flag_status,
            ]
        )
    return buf.getvalue()


def to_markdown(answers: list[AnswerRow], *, title: str = "Questionnaire response") -> str:
    """Serialize to a readable Markdown pack for review/submission."""
    answered = sum(1 for r in answers if _answered(r))
    need = len(answers) - answered
    lines = [
        f"# {title}",
        "",
        f"_{answered} of {len(answers)} questions answered from the corporate "
        f"Scope 3 inventory · {need} need human input._",
        "",
    ]
    for i, row in enumerate(answers, 1):
        key = f" `{row.framework_field_key}`" if row.framework_field_key else ""
        lines.append(f"**{i}.{key} {row.question_text}**")
        if _answered(row):
            lines.append(f"- Answer: {row.answer_text}")
            if row.citation:
                lines.append(f"- Source: {row.citation} (confidence {row.confidence_score:.0f})")
        else:
            lines.append(f"- {_NEEDS_HUMAN}")
        lines.append("")
    return "\n".join(lines)


def export_pack(
    answers: list[AnswerRow], fmt: str, *, title: str = "Questionnaire response"
) -> str:
    """Dispatch to a supported format. Returns the file content as text."""
    if fmt == "csv":
        return to_csv(answers)
    if fmt in ("markdown", "md"):
        return to_markdown(answers, title=title)
    raise ValueError(f"Unsupported export format: {fmt!r} (use 'csv' or 'markdown').")
