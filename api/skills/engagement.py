"""Engagement skill — supplier engagement workflows."""

from __future__ import annotations

from typing import Any

from api.agent.intake_forms import get_intake_form
from api.skills.base import Skill
from copilot.draft_email import run as draft_email
from copilot.models import EngagementCandidate
from copilot.suppliers_list import run as get_suppliers_list
from db.copilot_store import (
    Engagement,
    get_all_engagements,
    get_engagement,
    get_engagements_for_product,
)

_DEFAULT_TOP_N = 5


class EngagementSkill(Skill):
    name = "engagement"
    description = (
        "Supplier engagement workflows: list engagement candidates for a product, "
        "check engagement status, draft supplier data-request emails, and launch "
        "the Supplier Copilot module with an intake form."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "list_engagement_candidates",
                    "get_engagement_status",
                    "trigger_email_draft",
                    "launch_supplier_copilot",
                ],
                "description": "The engagement operation to perform.",
            },
            "access_token": {
                "type": "string",
                "description": "Supabase access token for the authenticated user.",
            },
            "product_name": {
                "type": "string",
                "description": "Product name for candidate listing or email drafting.",
            },
            "top_n": {
                "type": "integer",
                "description": "Max candidates to return (default 5).",
            },
            "engagement_id": {
                "type": "integer",
                "description": "Engagement ID (for get_engagement_status).",
            },
            "component": {
                "type": "string",
                "description": "Component name to identify a candidate for email drafting.",
            },
            "supplier_name": {
                "type": "string",
                "description": "Supplier name to identify a candidate for email drafting.",
            },
            "session_id": {
                "type": "string",
                "description": "Optional session ID for LLM logging.",
            },
        },
        "required": ["action", "access_token"],
    }

    async def run(self, action: str, **kwargs: Any) -> dict[str, Any]:
        handlers = {
            "list_engagement_candidates": self._list_engagement_candidates,
            "get_engagement_status": self._get_engagement_status,
            "trigger_email_draft": self._trigger_email_draft,
            "launch_supplier_copilot": self._launch_supplier_copilot,
        }
        handler = handlers.get(action)
        if handler is None:
            return _error(action, f"Unknown action: {action}")
        try:
            return handler(**kwargs)
        except Exception as exc:
            return _error(action, str(exc))

    def _list_engagement_candidates(
        self,
        *,
        access_token: str,
        product_name: str | None = None,
        top_n: int = _DEFAULT_TOP_N,
        **_: Any,
    ) -> dict[str, Any]:
        if not product_name or not product_name.strip():
            return _error(
                "list_engagement_candidates",
                "Provide a product_name.",
            )

        result = get_suppliers_list(
            product_name.strip(),
            top_n=max(top_n, 1),
            access_token=access_token,
        )
        if result.error:
            return _error("list_engagement_candidates", result.error)

        return _success(
            "list_engagement_candidates",
            {
                "product_name": result.product_name,
                "candidate_count": len(result.candidates),
                "candidates": [_candidate_dict(c) for c in result.candidates],
            },
        )

    def _get_engagement_status(
        self,
        *,
        access_token: str,
        engagement_id: int | None = None,
        product_name: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        if engagement_id is not None:
            engagement = get_engagement(engagement_id, access_token)
            if engagement is None:
                return _error(
                    "get_engagement_status",
                    f"Engagement {engagement_id} not found.",
                )
            return _success(
                "get_engagement_status",
                {
                    "count": 1,
                    "engagements": [_engagement_dict(engagement)],
                },
            )

        if product_name and product_name.strip():
            engagements = get_engagements_for_product(
                product_name.strip(),
                access_token,
            )
        else:
            engagements = get_all_engagements(access_token)

        return _success(
            "get_engagement_status",
            {
                "count": len(engagements),
                "engagements": [_engagement_dict(e) for e in engagements],
            },
        )

    def _trigger_email_draft(
        self,
        *,
        access_token: str,
        product_name: str | None = None,
        component: str | None = None,
        supplier_name: str | None = None,
        top_n: int = _DEFAULT_TOP_N,
        session_id: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        if not product_name or not product_name.strip():
            return _error("trigger_email_draft", "Provide a product_name.")

        list_result = get_suppliers_list(
            product_name.strip(),
            top_n=max(top_n, 1),
            access_token=access_token,
        )
        if list_result.error:
            return _error("trigger_email_draft", list_result.error)
        if not list_result.candidates:
            return _error(
                "trigger_email_draft",
                "No engagement candidates found for this product.",
            )

        candidate = _pick_candidate(
            list_result.candidates,
            component=component,
            supplier_name=supplier_name,
        )
        if candidate is None:
            return _error(
                "trigger_email_draft",
                "No candidate matched the provided component or supplier_name.",
            )

        draft_result = draft_email(
            candidate,
            list_result.product_name,
            session_id=session_id,
        )
        if draft_result.error:
            return _error("trigger_email_draft", draft_result.error)
        if draft_result.draft is None:
            return _error("trigger_email_draft", "Email draft generation failed.")

        return _success(
            "trigger_email_draft",
            {
                "product_name": list_result.product_name,
                "candidate": _candidate_dict(candidate),
                "to": draft_result.draft.to,
                "subject": draft_result.draft.subject,
                "body": draft_result.draft.body,
                "ghg_protocol_basis": draft_result.draft.ghg_protocol_basis,
                "citations": draft_result.citations,
            },
        )

    def _launch_supplier_copilot(self, **_: Any) -> dict[str, Any]:
        intake_form = get_intake_form("supplier_copilot")
        if intake_form is None:
            return _error(
                "launch_supplier_copilot",
                "Supplier Copilot intake form not found.",
            )
        return _success(
            "launch_supplier_copilot",
            {
                "module_launch": {
                    "module_type": "supplier_copilot",
                    "step": "intake",
                    "intake_form": intake_form,
                },
            },
        )


def _pick_candidate(
    candidates: list[EngagementCandidate],
    *,
    component: str | None,
    supplier_name: str | None,
) -> EngagementCandidate | None:
    component_lower = (component or "").strip().lower()
    supplier_lower = (supplier_name or "").strip().lower()

    if component_lower or supplier_lower:
        for candidate in candidates:
            comp_match = (
                not component_lower
                or (candidate.component or "").lower() == component_lower
            )
            supplier_match = (
                not supplier_lower
                or candidate.supplier_name.lower() == supplier_lower
            )
            if comp_match and supplier_match:
                return candidate
        return None

    return candidates[0]


def _candidate_dict(candidate: EngagementCandidate) -> dict[str, Any]:
    return {
        "supplier_name": candidate.supplier_name,
        "component": candidate.component,
        "material": candidate.material,
        "kg_co2e": candidate.kg_co2e,
        "share_pct": candidate.share_pct,
        "contact_found": candidate.contact_found,
        "contact_name": candidate.contact_name,
        "contact_email": candidate.contact_email,
        "existing_engagement_id": candidate.existing_engagement_id,
        "engagement_status": candidate.engagement_status,
    }


def _engagement_dict(engagement: Engagement) -> dict[str, Any]:
    return {
        "engagement_id": engagement.engagement_id,
        "supplier_name": engagement.supplier_name,
        "product_name": engagement.product_name,
        "component_name": engagement.component_name,
        "material": engagement.material,
        "kg_co2e": engagement.kg_co2e,
        "share_pct": engagement.share_pct,
        "status": engagement.status,
        "email_draft": engagement.email_draft,
        "email_sent": engagement.email_sent,
        "response_received": engagement.response_received,
        "routing_decision": engagement.routing_decision,
        "decision_rationale": engagement.decision_rationale,
        "ghg_protocol_citation": engagement.ghg_protocol_citation,
        "next_step": engagement.next_step,
        "created_at": engagement.created_at,
        "last_action_date": engagement.last_action_date,
    }


def _success(action: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"action": action, "success": True, "data": data}


def _error(action: str, message: str) -> dict[str, Any]:
    return {"action": action, "success": False, "error": message}


engagement_skill = EngagementSkill()
