"""Supabase CRUD for the Scope-3 questionnaire flow (Epic B).

Imports ONLY db.client; org_id resolved by the route. User-scoped client so RLS
(public.is_org_member(org_id)) applies. Written but NOT yet run against a live DB.
"""

from __future__ import annotations

from db.client import get_user_client


def create_request(*, access_token: str, org_id: str, user_id: str, fields: dict) -> dict:
    client = get_user_client(access_token)
    row = {"org_id": org_id, "user_id": user_id}
    row.update({k: v for k, v in fields.items() if v is not None})
    return client.table("s3_questionnaire_requests").insert(row).execute().data[0]


def list_requests(*, access_token: str, org_id: str) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_questionnaire_requests")
        .select("*")
        .eq("org_id", org_id)
        .order("request_id", desc=True)
        .execute()
    )
    return resp.data or []


def get_request(*, access_token: str, request_id: int) -> dict | None:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_questionnaire_requests")
        .select("*")
        .eq("request_id", request_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def update_request(*, access_token: str, request_id: int, patch: dict) -> dict | None:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_questionnaire_requests")
        .update({k: v for k, v in patch.items() if v is not None})
        .eq("request_id", request_id)
        .execute()
    )
    return resp.data[0] if resp.data else None


def replace_questions(
    *, access_token: str, org_id: str, request_id: int, questions: list[dict]
) -> int:
    """Replace the parsed questions for a request (re-detect is idempotent)."""
    client = get_user_client(access_token)
    client.table("s3_questionnaire_questions").delete().eq("request_id", request_id).execute()
    if not questions:
        return 0
    rows = [{"org_id": org_id, "request_id": request_id, **q} for q in questions]
    resp = client.table("s3_questionnaire_questions").insert(rows).execute()
    return len(resp.data or [])


def list_questions(*, access_token: str, request_id: int) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_questionnaire_questions")
        .select("*")
        .eq("request_id", request_id)
        .order("question_index")
        .execute()
    )
    return resp.data or []


def replace_mappings(
    *, access_token: str, org_id: str, question_ids: list[int], mappings: list[dict]
) -> int:
    """Replace mappings for the given questions (idempotent re-map)."""
    client = get_user_client(access_token)
    if question_ids:
        client.table("s3_question_datapoint_mappings").delete().in_(
            "question_id", question_ids
        ).execute()
    if not mappings:
        return 0
    rows = [{"org_id": org_id, **m} for m in mappings]
    resp = client.table("s3_question_datapoint_mappings").insert(rows).execute()
    return len(resp.data or [])


def list_mappings(*, access_token: str, question_ids: list[int]) -> list[dict]:
    if not question_ids:
        return []
    client = get_user_client(access_token)
    resp = (
        client.table("s3_question_datapoint_mappings")
        .select("*")
        .in_("question_id", question_ids)
        .execute()
    )
    return resp.data or []


def add_library_entries(
    *, access_token: str, org_id: str, user_id: str, entries: list[dict]
) -> int:
    if not entries:
        return 0
    client = get_user_client(access_token)
    rows = [{"org_id": org_id, "user_id": user_id, **e} for e in entries]
    resp = client.table("s3_answer_library").insert(rows).execute()
    return len(resp.data or [])
