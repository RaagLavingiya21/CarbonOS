"""Vision-LLM extraction of utility bills → normalized meter reads (PRD 5.1).

A utility bill is a *document*, not a row: one bill commonly carries several meters
and separate demand/energy line items, each with its own service period. Claude
reads the PDF/image and returns a bill header plus a `meters[]` array, every field
tagged with a 0–1 confidence. Structured output is forced with tool-use (reliable
JSON), matching the platform's raw-anthropic convention (llm/client.py). The LLM
call is injectable (`invoke`) so parsing, normalization, and confidence logic are
unit-testable — and eval-scorable — without an API key.

Each extracted meter is normalized to canonical MWh via s2_ingestion.normalize
(reusing the MBtu/CCF ambiguity guards for gas) and emitted as an
`ExtractedMeterRow`, the same shape the CSV path produces, so OCR bills flow into
the identical commit + true-up-dedup pipeline. Fields whose confidence is below
REVIEW_THRESHOLD — or that fail to normalize/parse — are flagged for human review
rather than silently trusted or dropped.

Isolated Scope 2 module: imports only the s2_ingestion.normalize leaf. It defines
its own REVIEW_THRESHOLD and models rather than importing Scope 1's OCR package.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable

from s2_ingestion.normalize import UnitConversionError, normalize_to_mwh

_MODEL = "claude-sonnet-4-6"
# Per-field confidence below this routes a bill to review. Overridable via env so
# the value calibrated by evals/scope2_ocr (run_calibration.py) can be deployed
# without a code change; defaults to the calibrated 0.85.
REVIEW_THRESHOLD = float(os.getenv("S2_OCR_REVIEW_THRESHOLD", "0.85"))

# Bill-level fields (one per document).
HEADER_FIELDS = ["utility_name", "account_number", "service_address"]

# Per-meter fields. `is_estimated_read` matters downstream: it feeds the true-up
# dedup (an estimated read is superseded by a same-period actual).
METER_FIELDS = [
    "meter_number",
    "energy_carrier",
    "service_period_start",
    "service_period_end",
    "consumption_quantity",
    "consumption_unit",
    "demand_kw",
    "total_cost_usd",
    "is_estimated_read",
]

# Fields a calc cannot proceed without — low confidence or absence here routes the
# whole bill to review (address/meter_number/demand missing does not).
CRITICAL_METER_FIELDS = [
    "energy_carrier",
    "service_period_start",
    "service_period_end",
    "consumption_quantity",
    "consumption_unit",
]

_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y")

# Synonyms a bill prints → the carrier vocabulary the DB constraint allows.
_CARRIER_SYNONYMS = {
    "electricity": "electricity",
    "electric": "electricity",
    "power": "electricity",
    "kwh": "electricity",
    "natural gas": "natural_gas",
    "natural_gas": "natural_gas",
    "gas": "natural_gas",
    "ng": "natural_gas",
    "steam": "steam",
    "heat": "heat",
    "cooling": "cooling",
    "chilled water": "cooling",
}


@dataclass(frozen=True)
class ExtractedField:
    value: str | None
    confidence: float  # 0.0-1.0


@dataclass
class MeterExtraction:
    """One meter/line item's fields as returned by the model (raw, pre-normalize)."""

    fields: dict[str, ExtractedField]

    def get(self, name: str) -> ExtractedField:
        return self.fields.get(name, ExtractedField(None, 0.0))

    def min_critical_confidence(self) -> float:
        populated = [
            self.get(n).confidence
            for n in CRITICAL_METER_FIELDS
            if self.get(n).value not in (None, "")
        ]
        return min(populated) if populated else 0.0


@dataclass
class BillExtraction:
    """A whole bill: header fields + one MeterExtraction per meter."""

    header: dict[str, ExtractedField]
    meters: list[MeterExtraction]
    model: str = ""
    error: str | None = None

    def to_dict(self) -> dict:
        """JSON-serializable form (for the preview DTO and eval labels)."""
        return {
            "header": {n: {"value": f.value, "confidence": f.confidence} for n, f in self.header.items()},
            "meters": [
                {n: {"value": f.value, "confidence": f.confidence} for n, f in m.fields.items()}
                for m in self.meters
            ],
            "model": self.model,
            "error": self.error,
        }


@dataclass(frozen=True)
class ExtractedMeterRow:
    """A normalized meter read — the CSV path's ParsedBill shape, plus review state."""

    meter_number: str | None
    energy_carrier: str | None
    period_start: date | None
    period_end: date | None
    raw_quantity: float | None
    raw_unit: str | None
    canonical_mwh: float | None
    cost_usd: float | None
    demand_kw: float | None
    is_estimated_read: bool
    is_cost_only: bool
    conversion_note: str | None
    min_confidence: float
    review_reasons: list[str] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return bool(self.review_reasons) or self.min_confidence < REVIEW_THRESHOLD


# --- tool schema + prompt --------------------------------------------------


def _field_schema(description: str) -> dict:
    return {
        "type": "object",
        "properties": {
            "value": {"type": ["string", "null"], "description": f"{description}, or null if absent"},
            "confidence": {"type": "number", "description": "certainty 0.0-1.0"},
        },
        "required": ["value", "confidence"],
    }


def extraction_tool() -> dict:
    """Anthropic tool schema forcing a header + meters[] with per-field confidence."""
    meter_props = {
        "meter_number": _field_schema("meter/point-of-delivery id"),
        "energy_carrier": _field_schema("electricity or natural gas (as printed)"),
        "service_period_start": _field_schema("service period start date"),
        "service_period_end": _field_schema("service period end date"),
        "consumption_quantity": _field_schema("metered consumption amount"),
        "consumption_unit": _field_schema("unit of consumption, e.g. kWh, therms, CCF, MMBtu"),
        "demand_kw": _field_schema("peak demand in kW, if billed"),
        "total_cost_usd": _field_schema("charge for this line, in USD"),
        "is_estimated_read": _field_schema("'true' if the read is estimated, else 'false'"),
    }
    return {
        "name": "record_bill_extraction",
        "description": "Return the utility-bill header and one entry per metered line item.",
        "input_schema": {
            "type": "object",
            "properties": {
                **{name: _field_schema(name.replace("_", " ")) for name in HEADER_FIELDS},
                "meters": {
                    "type": "array",
                    "description": "One object per meter/service period on the bill.",
                    "items": {
                        "type": "object",
                        "properties": meter_props,
                        "required": METER_FIELDS,
                    },
                },
            },
            "required": [*HEADER_FIELDS, "meters"],
        },
    }


def build_prompt() -> str:
    return (
        "Extract this utility bill using the record_bill_extraction tool. Return the "
        "account header and one entry per metered line item (a bill may list several "
        "meters or service periods — capture each separately). For every field give the "
        "literal value and your confidence (0.0-1.0). If a field is absent, return null "
        "with confidence 0. Report consumption_unit exactly as printed (do not convert). "
        "Do not guess; a low confidence is better than a wrong value."
    )


# --- parsing (pure) --------------------------------------------------------


def _clamp_confidence(raw: object, has_value: bool) -> float:
    try:
        c = max(0.0, min(1.0, float(raw)))
    except (TypeError, ValueError):
        c = 0.0
    return c if has_value else 0.0


def _to_field(item: object) -> ExtractedField:
    data = item if isinstance(item, dict) else {}
    raw_value = data.get("value")
    value = str(raw_value) if raw_value not in (None, "") else None
    return ExtractedField(value=value, confidence=_clamp_confidence(data.get("confidence"), value is not None))


def parse_extraction(tool_input: dict, *, model: str = _MODEL) -> BillExtraction:
    """Pure: validate the tool's JSON into a typed BillExtraction (clamps confidence)."""
    header = {name: _to_field(tool_input.get(name)) for name in HEADER_FIELDS}
    meters = [
        MeterExtraction(fields={name: _to_field((raw or {}).get(name)) for name in METER_FIELDS})
        for raw in tool_input.get("meters") or []
    ]
    return BillExtraction(header=header, meters=meters, model=model)


# --- normalization (pure) --------------------------------------------------


def _parse_float(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except ValueError:
        return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_bool(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "estimated"}


def _canonical_carrier(value: str | None) -> str | None:
    if not value:
        return None
    return _CARRIER_SYNONYMS.get(value.strip().lower())


def normalize_meter(meter: MeterExtraction) -> ExtractedMeterRow:
    """Turn one raw MeterExtraction into a normalized row with review reasons."""
    reasons: list[str] = []

    raw_carrier = meter.get("energy_carrier").value
    carrier = _canonical_carrier(raw_carrier)
    if raw_carrier and carrier is None:
        reasons.append(f"unrecognized energy carrier '{raw_carrier}'")

    period_start = _parse_date(meter.get("service_period_start").value)
    period_end = _parse_date(meter.get("service_period_end").value)
    if meter.get("service_period_start").value and period_start is None:
        reasons.append("could not parse service_period_start")
    if meter.get("service_period_end").value and period_end is None:
        reasons.append("could not parse service_period_end")
    if period_start and period_end and period_end < period_start:
        reasons.append("service_period_end precedes service_period_start")

    raw_quantity = _parse_float(meter.get("consumption_quantity").value)
    raw_unit = (meter.get("consumption_unit").value or "").strip() or None
    is_cost_only = raw_quantity is None or raw_quantity == 0.0

    canonical_mwh: float | None = None
    conversion_note: str | None = None
    if not is_cost_only:
        if not raw_unit:
            reasons.append("consumption present but unit is missing")
        else:
            try:
                normalized = normalize_to_mwh(raw_quantity, raw_unit)
                canonical_mwh = normalized.canonical_mwh
                conversion_note = normalized.conversion_note
            except UnitConversionError as exc:
                reasons.append(str(exc))

    for name in CRITICAL_METER_FIELDS:
        if meter.get(name).value in (None, ""):
            reasons.append(f"missing {name}")

    return ExtractedMeterRow(
        meter_number=meter.get("meter_number").value,
        energy_carrier=carrier,
        period_start=period_start,
        period_end=period_end,
        raw_quantity=raw_quantity,
        raw_unit=raw_unit,
        canonical_mwh=canonical_mwh,
        cost_usd=_parse_float(meter.get("total_cost_usd").value),
        demand_kw=_parse_float(meter.get("demand_kw").value),
        is_estimated_read=_parse_bool(meter.get("is_estimated_read").value),
        is_cost_only=is_cost_only,
        conversion_note=conversion_note,
        min_confidence=meter.min_critical_confidence(),
        review_reasons=reasons,
    )


def normalize_bill(extraction: BillExtraction) -> list[ExtractedMeterRow]:
    """Normalize every meter on a bill. Empty if extraction errored/had no meters."""
    return [normalize_meter(m) for m in extraction.meters]


def bill_review_reasons(extraction: BillExtraction, rows: list[ExtractedMeterRow]) -> list[str]:
    """Bill-level reasons to route a whole document to review.

    Per-meter `needs_review` can't catch a *total* failure: if the model errors or
    returns no meters, there are no rows to flag, so the bill would otherwise pass
    silently as "nothing to import". A submitted bill yielding zero meters is itself
    suspect and must be surfaced.
    """
    reasons: list[str] = []
    if extraction.error:
        reasons.append(f"extraction error: {extraction.error}")
    if not rows:
        reasons.append("no meters extracted from the document")
    return reasons


# --- live vision call ------------------------------------------------------


def _media_type(content_type: str | None) -> str:
    ct = (content_type or "").lower()
    if "pdf" in ct:
        return "application/pdf"
    if ct in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        return ct
    return "application/pdf"


def _invoke_claude(prompt: str, media_type: str, b64: str) -> dict:
    """Real Claude vision call returning the tool input. Requires ANTHROPIC_API_KEY."""
    import anthropic

    block_type = "document" if media_type == "application/pdf" else "image"
    doc_block = {"type": block_type, "source": {"type": "base64", "media_type": media_type, "data": b64}}
    resp = anthropic.Anthropic().messages.create(
        model=_MODEL,
        max_tokens=2048,
        tools=[extraction_tool()],
        tool_choice={"type": "tool", "name": "record_bill_extraction"},
        messages=[{"role": "user", "content": [doc_block, {"type": "text", "text": prompt}]}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use":
            return dict(block.input)
    raise ValueError("Claude did not return a record_bill_extraction tool call")


def extract_bill_document(
    file_bytes: bytes,
    content_type: str | None,
    *,
    invoke: Callable[[str, str, str], dict] | None = None,
) -> BillExtraction:
    """Extract a utility bill. `invoke(prompt, media_type, b64)` is injectable for
    tests/evals; defaults to the Claude vision call. LLM failure -> flagged, not raised."""
    invoke = invoke or _invoke_claude
    media_type = _media_type(content_type)
    b64 = base64.b64encode(file_bytes).decode()
    try:
        tool_input = invoke(build_prompt(), media_type, b64)
    except Exception as exc:  # LLM/network failure -> flag for review, don't crash
        return BillExtraction(header={}, meters=[], model=_MODEL, error=str(exc))
    return parse_extraction(tool_input)


__all__ = [
    "REVIEW_THRESHOLD",
    "HEADER_FIELDS",
    "METER_FIELDS",
    "CRITICAL_METER_FIELDS",
    "ExtractedField",
    "MeterExtraction",
    "BillExtraction",
    "ExtractedMeterRow",
    "extraction_tool",
    "build_prompt",
    "parse_extraction",
    "normalize_meter",
    "normalize_bill",
    "extract_bill_document",
]
