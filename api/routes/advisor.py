"""FastAPI routes for the conversational footprint advisor."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends

from api.middleware.auth import CurrentUser, get_current_user
from api.models.schemas import AdvisorChatRequest, AdvisorChatResponse
from db.reader import build_llm_context
from llm.client import ask_advisor

router = APIRouter(tags=["advisor"])


@router.post("/api/advisor/chat", response_model=AdvisorChatResponse)
def chat(
    request: AdvisorChatRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> AdvisorChatResponse:
    session_id = request.session_id or str(uuid4())
    history = [message.model_dump() for message in request.conversation_history]
    db_context = build_llm_context(current_user.access_token)
    response = ask_advisor(
        user_message=request.user_message,
        conversation_history=history,
        db_context=db_context,
        session_id=session_id,
    )
    return AdvisorChatResponse(
        session_id=session_id,
        content=response.content,
        has_data_reference=response.has_data_reference,
        citations=response.citations,
        error=response.error,
    )
