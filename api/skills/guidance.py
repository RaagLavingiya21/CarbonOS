"""Guidance skill — GHG Protocol RAG retrieval and methodology Q&A."""

from __future__ import annotations

from typing import Any

from api.skills.base import Skill
from llm.client import AdvisorResponse, ask_advisor
from rag.retriever import IndexNotBuiltError, retrieve

_NO_PRODUCT_DATA = "No saved product analyses are available for this session."


class GuidanceSkill(Skill):
    name = "guidance"
    description = (
        "Answer GHG Protocol and Scope 3 methodology questions using the "
        "retrieval index and the existing advisor Q&A flow."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["retrieve", "ask"],
                "description": (
                    "retrieve: fetch GHG Protocol excerpts only; "
                    "ask: full RAG-grounded Q&A via the advisor."
                ),
            },
            "query": {
                "type": "string",
                "description": "User question or search query.",
            },
            "user_message": {
                "type": "string",
                "description": "User message for ask (alias for query).",
            },
            "conversation_history": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
                "description": "Prior conversation turns for ask.",
            },
            "n_results": {
                "type": "integer",
                "description": "Number of RAG chunks to retrieve (default 4).",
            },
            "session_id": {
                "type": "string",
                "description": "Optional session ID for LLM logging.",
            },
            "access_token": {
                "type": "string",
                "description": (
                    "Optional Supabase token; when provided, ask may combine "
                    "product data with GHG guidance via the advisor router."
                ),
            },
        },
        "required": ["action"],
    }

    async def run(self, action: str, **kwargs: Any) -> dict[str, Any]:
        handlers = {
            "retrieve": self._retrieve,
            "ask": self._ask,
        }
        handler = handlers.get(action)
        if handler is None:
            return _error(action, f"Unknown action: {action}")
        try:
            return handler(**kwargs)
        except Exception as exc:
            return _error(action, str(exc))

    def _retrieve(
        self,
        *,
        query: str | None = None,
        user_message: str | None = None,
        n_results: int = 4,
        **_: Any,
    ) -> dict[str, Any]:
        text = (query or user_message or "").strip()
        if not text:
            return _error("retrieve", "Provide a query or user_message.")

        try:
            results = retrieve(text, n_results=max(n_results, 1))
        except IndexNotBuiltError as exc:
            return _error("retrieve", str(exc))

        return _success(
            "retrieve",
            {
                "query": text,
                "chunk_count": len(results),
                "citations": [r.source_citation for r in results],
                "chunks": [_chunk_dict(r) for r in results],
            },
        )

    def _ask(
        self,
        *,
        query: str | None = None,
        user_message: str | None = None,
        conversation_history: list[dict] | None = None,
        session_id: str | None = None,
        access_token: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        message = (user_message or query or "").strip()
        if not message:
            return _error("ask", "Provide a user_message or query.")

        db_context = _NO_PRODUCT_DATA
        if access_token:
            from db.reader import build_llm_context

            db_context = build_llm_context(access_token)

        response = ask_advisor(
            user_message=message,
            conversation_history=conversation_history or [],
            db_context=db_context,
            session_id=session_id,
        )
        return _success("ask", _advisor_dict(response))


def _chunk_dict(result: Any) -> dict[str, Any]:
    return {
        "text": result.text,
        "source_citation": result.source_citation,
        "chapter_num": result.chapter_num,
        "chapter_title": result.chapter_title,
        "section_num": result.section_num,
        "section_title": result.section_title,
        "start_page": result.start_page,
        "end_page": result.end_page,
        "category_num": result.category_num,
        "category_name": result.category_name,
        "topic_tags": result.topic_tags,
        "distance": result.distance,
    }


def _advisor_dict(response: AdvisorResponse) -> dict[str, Any]:
    return {
        "content": response.content,
        "has_data_reference": response.has_data_reference,
        "citations": response.citations,
        "error": response.error,
    }


def _success(action: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"action": action, "success": True, "data": data}


def _error(action: str, message: str) -> dict[str, Any]:
    return {"action": action, "success": False, "error": message}


guidance_skill = GuidanceSkill()
