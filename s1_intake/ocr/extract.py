"""Vision-LLM extraction: Claude reads a bill/invoice and returns fields+confidence.

Uses Claude tool-use for structured output (reliable JSON), matching the
platform's raw-anthropic convention (llm/client.py). The LLM call is injectable
(`invoke`) so the parsing/confidence logic is unit-testable without an API key.
"""

from __future__ import annotations

import base64
from typing import Callable

from s1_intake.ocr.models import REVIEW_THRESHOLD, ExtractedField, Extraction

_MODEL = "claude-sonnet-4-6"

# Extraction schemas (research/2.3 section B2).
UTILITY_FIELDS = [
    "account_number", "utility_name", "service_address",
    "billing_period_start", "billing_period_end",
    "consumption_quantity", "consumption_unit", "total_cost",
]
FUEL_FIELDS = [
    "supplier", "invoice_number", "delivery_date",
    "fuel_type", "quantity", "unit", "unit_price",
]


def fields_for(doc_kind: str) -> list[str]:
    return UTILITY_FIELDS if doc_kind == "utility_bill" else FUEL_FIELDS


def extraction_tool(doc_kind: str) -> dict:
    """Anthropic tool schema forcing structured value+confidence per field."""
    field_schema = {
        "type": "object",
        "properties": {
            "value": {"type": ["string", "null"], "description": "extracted value, or null if absent"},
            "confidence": {"type": "number", "description": "certainty 0.0-1.0"},
        },
        "required": ["value", "confidence"],
    }
    return {
        "name": "record_extraction",
        "description": f"Return the fields extracted from the {doc_kind.replace('_', ' ')}.",
        "input_schema": {
            "type": "object",
            "properties": {name: field_schema for name in fields_for(doc_kind)},
            "required": fields_for(doc_kind),
        },
    }


def build_prompt(doc_kind: str) -> str:
    return (
        f"Extract the fields from this {doc_kind.replace('_', ' ')} using the "
        "record_extraction tool. For each field give the literal value and your "
        "confidence (0.0-1.0). If a field is not present, return null with "
        "confidence 0. Do not guess; low confidence is better than a wrong value."
    )


def parse_extraction(tool_input: dict, doc_kind: str) -> Extraction:
    """Pure: validate the tool's JSON into a typed Extraction (clamps confidence)."""
    fields: dict[str, ExtractedField] = {}
    for name in fields_for(doc_kind):
        item = tool_input.get(name) or {}
        raw_value = item.get("value")
        value = str(raw_value) if raw_value not in (None, "") else None
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0
        fields[name] = ExtractedField(value=value, confidence=confidence if value else 0.0)
    return Extraction(doc_kind=doc_kind, fields=fields, model=_MODEL)


def _media_type(content_type: str | None) -> str:
    ct = (content_type or "").lower()
    if "pdf" in ct:
        return "application/pdf"
    if ct in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        return ct
    return "application/pdf"


def _invoke_claude(prompt: str, doc_kind: str, media_type: str, b64: str) -> dict:
    """Real Claude vision call returning the tool input. Requires ANTHROPIC_API_KEY."""
    import anthropic

    block_type = "document" if media_type == "application/pdf" else "image"
    doc_block = {
        "type": block_type,
        "source": {"type": "base64", "media_type": media_type, "data": b64},
    }
    resp = anthropic.Anthropic().messages.create(
        model=_MODEL,
        max_tokens=1024,
        tools=[extraction_tool(doc_kind)],
        tool_choice={"type": "tool", "name": "record_extraction"},
        messages=[{"role": "user", "content": [doc_block, {"type": "text", "text": prompt}]}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    raise ValueError("Claude did not return a record_extraction tool call")


def extract_document(
    file_bytes: bytes,
    content_type: str | None,
    doc_kind: str,
    *,
    invoke: Callable[[str, str, str, str], dict] | None = None,
) -> Extraction:
    """Extract fields from a document. `invoke(prompt, doc_kind, media_type, b64)`
    is injectable for tests; defaults to the Claude vision call."""
    invoke = invoke or _invoke_claude
    media_type = _media_type(content_type)
    b64 = base64.b64encode(file_bytes).decode()
    try:
        tool_input = invoke(build_prompt(doc_kind), doc_kind, media_type, b64)
    except Exception as exc:  # LLM/network failure -> flag for review, don't crash
        return Extraction(doc_kind=doc_kind, fields={}, error=str(exc))
    return parse_extraction(tool_input, doc_kind)


__all__ = [
    "REVIEW_THRESHOLD", "UTILITY_FIELDS", "FUEL_FIELDS", "fields_for",
    "extraction_tool", "build_prompt", "parse_extraction", "extract_document",
]
