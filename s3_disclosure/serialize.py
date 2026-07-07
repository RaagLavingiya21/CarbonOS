"""Render a DisclosureResult to a dependency-free pack (Markdown / CSV).

iXBRL tagging (ESEF) is deferred — it needs a bought tagging library (plan G).
"""

from __future__ import annotations

import csv
import io

from s3_disclosure.models import DisclosureResult


def _cell(dp) -> str:
    if dp.value is not None:
        return f"{dp.value:,.3f} {dp.unit}"
    if dp.text is not None:
        return dp.text
    return "⚠ MISSING"


def to_markdown(result: DisclosureResult) -> str:
    tag = " · PROVISIONAL" if result.is_provisional else ""
    lines = [
        f"# {result.framework} — Scope 3 disclosure{tag}",
        f"_Format {result.format_version}. Numbers sourced from the corporate Scope 3 inventory._",
        "",
    ]
    for n in result.notes:
        lines.append(f"> {n}")
    if result.notes:
        lines.append("")
    for dp in result.datapoints:
        lines.append(f"- **{dp.label}** (`{dp.key}`): {_cell(dp)}")
        if dp.source_ref:
            lines.append(f"  - Source: {dp.source_ref}")
    if result.category_breakdown:
        lines.append("")
        lines.append("## Scope 3 category breakdown")
        for dp in result.category_breakdown:
            lines.append(f"- {dp.label}: {_cell(dp)}")
    return "\n".join(lines)


def to_csv(result: DisclosureResult) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["key", "label", "value", "unit", "source", "flag"])
    for dp in list(result.datapoints) + list(result.category_breakdown):
        value = dp.value if dp.value is not None else (dp.text or "")
        w.writerow([dp.key, dp.label, value, dp.unit, dp.source_ref or "", dp.flag])
    return buf.getvalue()
