"""Tests for the Scope 1 OCR pipeline: pure extraction + the LangGraph workflow.

The Claude vision call is always injected/monkeypatched — no API key needed.
"""

from __future__ import annotations

import pytest

from s1_intake.ocr import extract_document, fields_for, parse_extraction
from s1_intake.ocr.extract import extraction_tool
from s1_intake.ocr.models import ExtractedField, Extraction


@pytest.fixture(autouse=True)
def _ocr_memory_checkpointer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Module-local: run the Scope 1 OCR graph on an in-memory checkpointer (no
    Postgres). Kept out of the shared conftest so nothing of ours lives there."""
    from langgraph.checkpoint.memory import MemorySaver

    from api.graphs import scope1_ocr_graph

    monkeypatch.setattr(scope1_ocr_graph, "get_checkpointer", lambda: MemorySaver())
    scope1_ocr_graph._ocr_graph = None

# --- Pure extraction --------------------------------------------------------

def test_extraction_tool_schema_lists_fields() -> None:
    tool = extraction_tool("utility_bill")
    props = tool["input_schema"]["properties"]
    assert set(props) == set(fields_for("utility_bill"))
    assert props["consumption_quantity"]["required"] == ["value", "confidence"]


def test_parse_extraction_clamps_and_nulls() -> None:
    tool_input = {
        "account_number": {"value": "12345", "confidence": 0.98},
        "consumption_quantity": {"value": "1000", "confidence": 1.7},   # clamps to 1.0
        "consumption_unit": {"value": "therms", "confidence": 0.6},
        "total_cost": {"value": None, "confidence": 0.9},               # null -> conf 0
    }
    ext = parse_extraction(tool_input, "utility_bill")
    assert ext.fields["account_number"].value == "12345"
    assert ext.fields["consumption_quantity"].confidence == 1.0
    assert ext.fields["total_cost"].value is None
    assert ext.fields["total_cost"].confidence == 0.0
    assert ext.min_confidence == 0.6                                    # lowest populated


def test_needs_review_threshold() -> None:
    low = Extraction("utility_bill", {"consumption_quantity": ExtractedField("1000", 0.6)})
    high = Extraction("utility_bill", {"consumption_quantity": ExtractedField("1000", 0.95)})
    assert low.needs_review() is True
    assert high.needs_review() is False


def test_extract_document_with_injected_llm() -> None:
    def fake_invoke(prompt, doc_kind, media_type, b64):
        return {"consumption_quantity": {"value": "1000", "confidence": 0.95},
                "consumption_unit": {"value": "therms", "confidence": 0.95}}

    ext = extract_document(b"pdf", "application/pdf", "utility_bill", invoke=fake_invoke)
    assert ext.error is None
    assert ext.fields["consumption_quantity"].value == "1000"
    assert ext.needs_review() is False


def test_extract_document_llm_failure_flags_review() -> None:
    def boom(*a, **k):
        raise RuntimeError("api down")

    ext = extract_document(b"pdf", "application/pdf", "utility_bill", invoke=boom)
    assert ext.error == "api down"
    assert ext.needs_review() is True          # failure -> human review, no crash


# --- LangGraph workflow (extract -> review pause -> resume) -----------------

def _fake_extract(fields):
    def _inner(file_bytes, content_type, doc_kind, **kwargs):
        return Extraction(doc_kind=doc_kind, fields=fields)
    return _inner


def test_graph_low_confidence_pauses_at_review(monkeypatch) -> None:
    from api.graphs import scope1_ocr_graph as ocr_graph

    monkeypatch.setattr(
        ocr_graph, "extract_document",
        _fake_extract({"consumption_quantity": ExtractedField("1000", 0.6),
                       "consumption_unit": ExtractedField("therms", 0.95)}),
    )
    state = ocr_graph.start_ocr("sess-low", "utility_bill", "Zm9v", "application/pdf")
    assert state["needs_review"] is True
    assert state["phase"] == "review"                      # paused at the checkpoint

    # reviewer corrects a field and approves -> graph resumes to approved
    resumed = ocr_graph.review_ocr("sess-low", "approve", {"consumption_quantity": "1050"})
    assert resumed["phase"] == "approved"
    assert resumed["extraction"]["consumption_quantity"]["value"] == "1050"
    assert resumed["extraction"]["consumption_quantity"]["confidence"] == 1.0   # human-verified


def test_graph_high_confidence_auto_approves(monkeypatch) -> None:
    from api.graphs import scope1_ocr_graph as ocr_graph

    monkeypatch.setattr(
        ocr_graph, "extract_document",
        _fake_extract({"consumption_quantity": ExtractedField("1000", 0.96),
                       "consumption_unit": ExtractedField("therms", 0.97)}),
    )
    state = ocr_graph.start_ocr("sess-high", "utility_bill", "Zm9v", "application/pdf")
    assert state["needs_review"] is False
    assert state["phase"] == "approved"                    # no human checkpoint


def test_graph_reject(monkeypatch) -> None:
    from api.graphs import scope1_ocr_graph as ocr_graph

    monkeypatch.setattr(
        ocr_graph, "extract_document",
        _fake_extract({"consumption_quantity": ExtractedField("1000", 0.4)}),
    )
    ocr_graph.start_ocr("sess-rej", "utility_bill", "Zm9v", "application/pdf")
    resumed = ocr_graph.review_ocr("sess-rej", "reject")
    assert resumed["phase"] == "rejected"
