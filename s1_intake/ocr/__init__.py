"""Vision-LLM OCR for utility bills and fuel invoices (Phase 2).

A single Claude vision call with tool-based structured output returns each field
with a confidence; anything below the review threshold routes to a human queue.
The LangGraph workflow lives in api/graphs/ocr_graph.py; this package is the
framework-free extraction core (pure parse + confidence logic, injectable LLM
call). See research/2.3 section B2.
"""

from s1_intake.ocr.extract import (
    REVIEW_THRESHOLD,
    extract_document,
    fields_for,
    parse_extraction,
)
from s1_intake.ocr.models import ExtractedField, Extraction

__all__ = [
    "REVIEW_THRESHOLD",
    "ExtractedField",
    "Extraction",
    "extract_document",
    "fields_for",
    "parse_extraction",
]
