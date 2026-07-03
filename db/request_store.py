"""Supabase CRUD for inbound PCF requests (Wave 2 Workstream R).

Public request creation uses the service-role client with input validation.
Authenticated inbox operations use the user-scoped client (RLS org-member policies).
"""

from __future__ import annotations

from db.client import get_service_client, get_user_client
from db.copilot_store import append_audit_log
from db.org_store import get_active_org, get_active_org_member_ids
from db.reader import get_product_by_id
from db.share_store import create_share

_MAX_TEXT_LEN = 2000

_REQUEST_COLUMNS = (
    "request_id, org_id, requester_name, requester_email, requester_company, "
    "product_name, message, status, fulfilled_share_id, created_at"
)


def _cap_text(value: str | None, *, field: str) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if len(text) > _MAX_TEXT_LEN:
        raise ValueError(f"{field} must be at most {_MAX_TEXT_LEN} characters.")
    return text


def create_request(
    org_id: str,
    *,
    requester_name: str | None,
    requester_email: str | None,
    requester_company: str | None,
    product_name: str | None,
    message: str | None,
) -> int:
    """Insert an open PCF request via the service client (public form path).

    Known limitation: no rate-limiting infrastructure — inputs are length-capped
    and validated instead.
    """
    client = get_service_client()
    org_response = (
        client.table("organizations")
        .select("id")
        .eq("id", org_id)
        .limit(1)
        .execute()
    )
    if not org_response.data:
        raise ValueError(f"Organization '{org_id}' not found.")

    row = {
        "org_id": org_id,
        "requester_name": _cap_text(requester_name, field="requester_name"),
        "requester_email": _cap_text(requester_email, field="requester_email"),
        "requester_company": _cap_text(requester_company, field="requester_company"),
        "product_name": _cap_text(product_name, field="product_name"),
        "message": _cap_text(message, field="message"),
        "status": "open",
    }
    response = client.table("pcf_requests").insert(row).execute()
    return int(response.data[0]["request_id"])


def list_requests_for_org(access_token: str, *, user_id: str | None = None) -> list[dict]:
    """Return PCF requests for the caller's active org (org-scoped inbox)."""
    member_ids = get_active_org_member_ids(access_token, user_id=user_id)
    if not member_ids:
        return []

    org = get_active_org(access_token, user_id=user_id)
    if org is None:
        return []

    client = get_user_client(access_token)
    response = (
        client.table("pcf_requests")
        .select(_REQUEST_COLUMNS)
        .eq("org_id", org.id)
        .order("created_at", desc=True)
        .execute()
    )
    rows = response.data
    share_ids = [
        int(row["fulfilled_share_id"])
        for row in rows
        if row.get("fulfilled_share_id") is not None
    ]
    share_tokens: dict[int, str] = {}
    if share_ids:
        share_response = (
            client.table("footprint_shares")
            .select("share_id, share_token")
            .in_("share_id", share_ids)
            .execute()
        )
        share_tokens = {
            int(item["share_id"]): str(item["share_token"]) for item in share_response.data
        }

    enriched: list[dict] = []
    for row in rows:
        item = dict(row)
        share_id = item.get("fulfilled_share_id")
        if share_id is not None:
            item["share_token"] = share_tokens.get(int(share_id))
        enriched.append(item)
    return enriched


def fulfil_request(
    request_id: int,
    product_id: int,
    *,
    user_id: str,
    access_token: str,
) -> dict:
    """Attach a published footprint share to an open request and mark it fulfilled."""
    org = get_active_org(access_token, user_id=user_id)
    if org is None:
        raise ValueError("No active organization for this user.")

    client = get_user_client(access_token)
    lookup = (
        client.table("pcf_requests")
        .select(_REQUEST_COLUMNS)
        .eq("request_id", request_id)
        .limit(1)
        .execute()
    )
    if not lookup.data:
        raise ValueError(f"Request {request_id} not found.")
    request_row = lookup.data[0]
    if str(request_row["org_id"]) != org.id:
        raise ValueError(f"Request {request_id} is not in your active organization.")
    if request_row.get("status") != "open":
        raise ValueError(f"Request {request_id} is not open.")

    product = get_product_by_id(product_id, access_token)
    if product is None:
        raise ValueError(f"Analysis {product_id} not found.")
    if product.get("status") != "published":
        raise ValueError("Only published footprints can fulfil a request.")

    recipient_parts = [
        request_row.get("requester_name"),
        request_row.get("requester_company"),
        request_row.get("requester_email"),
    ]
    recipient_label = " · ".join(part for part in recipient_parts if part) or None

    share = create_share(
        product_id,
        recipient_label=recipient_label,
        user_id=user_id,
        access_token=access_token,
    )

    client.table("pcf_requests").update(
        {
            "status": "fulfilled",
            "fulfilled_share_id": share["share_id"],
        }
    ).eq("request_id", request_id).execute()

    append_audit_log(
        "pcf_request_fulfilled",
        "pcf_request",
        user_id=user_id,
        access_token=access_token,
        product_name=product.get("product_name"),
        supplier_name=request_row.get("requester_company"),
        status="fulfilled",
        decision_rationale=request_row.get("message"),
    )

    return {
        "request_id": request_id,
        "status": "fulfilled",
        "share_id": share["share_id"],
        "share_token": share["share_token"],
    }


def decline_request(request_id: int, *, user_id: str, access_token: str) -> dict:
    """Mark an open PCF request as declined."""
    org = get_active_org(access_token, user_id=user_id)
    if org is None:
        raise ValueError("No active organization for this user.")

    client = get_user_client(access_token)
    lookup = (
        client.table("pcf_requests")
        .select(_REQUEST_COLUMNS)
        .eq("request_id", request_id)
        .limit(1)
        .execute()
    )
    if not lookup.data:
        raise ValueError(f"Request {request_id} not found.")
    request_row = lookup.data[0]
    if str(request_row["org_id"]) != org.id:
        raise ValueError(f"Request {request_id} is not in your active organization.")
    if request_row.get("status") != "open":
        raise ValueError(f"Request {request_id} is not open.")

    client.table("pcf_requests").update({"status": "declined"}).eq(
        "request_id", request_id
    ).execute()

    append_audit_log(
        "pcf_request_declined",
        "pcf_request",
        user_id=user_id,
        access_token=access_token,
        product_name=request_row.get("product_name"),
        supplier_name=request_row.get("requester_company"),
        status="declined",
    )

    return {"request_id": request_id, "status": "declined"}
