"""LangGraph StateGraph for the Scope 1 OCR extraction + human-review workflow.

Flow: extract (Claude vision) -> confidence gate. High-confidence extractions go
straight to `approved`; low-confidence ones pause at a human-review checkpoint
(interrupt_before) until a reviewer resumes with corrections + approve/reject.
Mirrors api/graphs/gap_analyzer_graph.py. The record write happens in the route
on approval (auth stays out of the checkpointer).
"""

from __future__ import annotations

import base64
from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from api.graphs.checkpointer import get_checkpointer
from api.graphs.helpers import get_graph_values, invoke_graph, update_graph_state
from s1_intake.ocr import REVIEW_THRESHOLD, extract_document

OcrPhase = Literal["extracting", "review", "approved", "rejected", "done"]


class OcrState(TypedDict, total=False):
    session_id: str
    doc_kind: str
    file_b64: str | None
    content_type: str | None
    extraction: dict | None          # {field: {value, confidence}}
    min_confidence: float
    needs_review: bool
    phase: OcrPhase
    corrected_fields: dict | None
    review_action: Literal["approve", "reject"] | None


def _extract_node(state: OcrState) -> dict:
    b64 = state.get("file_b64") or ""
    file_bytes = base64.b64decode(b64) if b64 else b""
    result = extract_document(file_bytes, state.get("content_type"), state["doc_kind"])
    needs_review = result.needs_review(REVIEW_THRESHOLD)
    return {
        "extraction": result.to_dict(),
        "min_confidence": result.min_confidence,
        "needs_review": needs_review,
        "phase": "review" if needs_review else "approved",
        "file_b64": None,            # drop the blob from checkpointed state
    }


def _human_review_node(state: OcrState) -> dict:
    action = state.get("review_action", "approve")
    if action == "reject":
        return {"phase": "rejected", "review_action": None}

    extraction = dict(state.get("extraction") or {})
    for name, value in (state.get("corrected_fields") or {}).items():
        extraction[name] = {"value": value, "confidence": 1.0}   # human-verified
    return {
        "extraction": extraction,
        "phase": "approved",
        "review_action": None,
        "corrected_fields": None,
    }


def _route_after_extract(state: OcrState) -> str:
    return "human_review" if state.get("needs_review") else "done"


def _build_ocr_graph():
    builder = StateGraph(OcrState)
    builder.add_node("extract", _extract_node)
    builder.add_node("human_review", _human_review_node)

    builder.add_edge(START, "extract")
    builder.add_conditional_edges(
        "extract", _route_after_extract, {"human_review": "human_review", "done": END}
    )
    builder.add_edge("human_review", END)

    return builder.compile(
        checkpointer=get_checkpointer(),
        interrupt_before=["human_review"],
    )


_ocr_graph = None


def get_ocr_graph():
    global _ocr_graph
    if _ocr_graph is None:
        _ocr_graph = _build_ocr_graph()
    return _ocr_graph


def start_ocr(session_id: str, doc_kind: str, file_b64: str, content_type: str | None) -> OcrState:
    """Run extraction; pause at review for low-confidence, else reach 'approved'."""
    graph = get_ocr_graph()
    initial: OcrState = {
        "session_id": session_id,
        "doc_kind": doc_kind,
        "file_b64": file_b64,
        "content_type": content_type,
        "extraction": None,
        "phase": "extracting",
        "review_action": None,
        "corrected_fields": None,
    }
    return invoke_graph(graph, session_id, initial)


def review_ocr(
    session_id: str,
    action: Literal["approve", "reject"],
    corrected_fields: dict | None = None,
) -> OcrState:
    """Resume from the human-review checkpoint with corrections + approve/reject."""
    graph = get_ocr_graph()
    update_graph_state(
        graph, session_id, {"review_action": action, "corrected_fields": corrected_fields or {}}
    )
    return invoke_graph(graph, session_id, None)


def get_ocr_state(session_id: str) -> OcrState | None:
    return get_graph_values(get_ocr_graph(), session_id)
