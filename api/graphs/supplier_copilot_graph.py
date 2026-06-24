"""LangGraph StateGraphs for the Supplier Engagement Copilot workflows."""

from __future__ import annotations

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from api.graphs.checkpointer import get_checkpointer
from api.graphs.helpers import get_graph_values, invoke_graph, update_graph_state
from copilot.draft_email import run as draft_email_run
from copilot.exception_router import (
    DRAFT_FOLLOW_UP,
    ESCALATE,
    FLAG_FOR_HUMAN,
    STORE_DATA,
)
from copilot.exception_router import (
    run as route_exception_run,
)
from copilot.models import (
    EmailDraftResult,
    EngagementCandidate,
    ParseResponseResult,
    RoutingResult,
    SuppliersListResult,
)
from copilot.parse_response import run as parse_response_run
from copilot.suppliers_list import run as suppliers_list_run
from db.copilot_store import (
    append_audit_log,
    create_engagement,
    get_engagement,
    update_engagement,
)

CopilotPhase = Literal[
    "selecting",
    "drafting",
    "email_review",
    "sent",
    "processing",
    "routing_review",
    "routed",
    "done",
]

_STATUS_BY_ACTION = {
    STORE_DATA: "closed",
    DRAFT_FOLLOW_UP: "follow-up",
    FLAG_FOR_HUMAN: "flagged",
    ESCALATE: "flagged",
}


class EmailDraftState(TypedDict, total=False):
    session_id: str
    user_id: str
    access_token: str
    product_name: str
    candidate: EngagementCandidate | None
    suppliers_result: SuppliersListResult | None
    email_draft_result: EmailDraftResult | None
    phase: CopilotPhase
    email_approved: bool
    email_body: str | None
    engagement_id: int | None


class ResponseRoutingState(TypedDict, total=False):
    session_id: str
    user_id: str
    access_token: str
    engagement_id: int
    supplier_name: str
    component: str | None
    response_text: str
    days_since_contact: int
    parse_result: ParseResponseResult | None
    routing_result: RoutingResult | None
    phase: CopilotPhase
    auto_apply: bool
    route_approved: bool
    engagement_status: str | None


def _select_supplier_node(state: EmailDraftState) -> dict:
    product_name = state["product_name"]
    if state.get("candidate") is not None:
        return {"phase": "drafting", "suppliers_result": None}

    result = suppliers_list_run(
        product_name,
        top_n=10,
        access_token=state["access_token"],
    )
    candidate = result.candidates[0] if result.candidates else None
    return {
        "suppliers_result": result,
        "candidate": candidate,
        "phase": "drafting" if candidate else "selecting",
    }


def _draft_email_node(state: EmailDraftState) -> dict:
    candidate = state.get("candidate")
    if candidate is None:
        return {
            "email_draft_result": EmailDraftResult(
                draft=None,
                citations=[],
                error="No supplier candidate available for email drafting.",
            ),
            "phase": "email_review",
        }

    result = draft_email_run(
        candidate,
        state["product_name"],
        session_id=state["session_id"],
    )
    return {"email_draft_result": result, "phase": "email_review"}


def _human_review_email_node(state: EmailDraftState) -> dict:
    return {"email_approved": state.get("email_approved", False), "phase": "email_review"}


def _send_email_node(state: EmailDraftState) -> dict:
    candidate = state.get("candidate")
    draft_result = state.get("email_draft_result")
    body = state.get("email_body")

    if candidate is None or draft_result is None or draft_result.draft is None:
        return {"phase": "done"}

    email_body = body or draft_result.draft.body
    engagement_id = create_engagement(
        supplier_name=candidate.supplier_name,
        product_name=state["product_name"],
        component_name=candidate.component,
        material=candidate.material,
        kg_co2e=candidate.kg_co2e,
        share_pct=candidate.share_pct,
        user_id=state["user_id"],
        access_token=state["access_token"],
        email_draft=email_body,
    )
    append_audit_log(
        event="email_drafted",
        workflow="draft_email",
        user_id=state["user_id"],
        access_token=state["access_token"],
        supplier_name=candidate.supplier_name,
        product_name=state["product_name"],
        component_name=candidate.component,
        email_sent=email_body,
        status="open",
    )
    return {"engagement_id": engagement_id, "phase": "sent"}


def _route_after_send(state: EmailDraftState) -> str:
    if state.get("email_approved"):
        return "send_email"
    return "done"


def _process_response_node(state: ResponseRoutingState) -> dict:
    parse_result = parse_response_run(
        response_text=state["response_text"],
        supplier_name=state["supplier_name"],
        component=state.get("component"),
        session_id=state["session_id"],
    )
    phase: CopilotPhase = "processing" if parse_result.error else "routing_review"
    return {"parse_result": parse_result, "phase": phase}


def _route_response_node(state: ResponseRoutingState) -> dict:
    parse_result = state.get("parse_result")
    if parse_result is None or parse_result.parsed is None:
        return {"routing_result": None, "phase": "done"}

    routing_result = route_exception_run(
        parsed=parse_result.parsed,
        supplier_name=state["supplier_name"],
        component=state.get("component"),
        days_since_contact=state.get("days_since_contact", 0),
        session_id=state["session_id"],
    )
    return {"routing_result": routing_result, "phase": "routing_review"}


def _human_review_route_node(state: ResponseRoutingState) -> dict:
    return {"route_approved": state.get("route_approved", False), "phase": "routing_review"}


def _apply_routing_node(state: ResponseRoutingState) -> dict:
    parse_result = state.get("parse_result")
    routing_result = state.get("routing_result")
    engagement_id = state["engagement_id"]
    access_token = state["access_token"]

    if parse_result is None or parse_result.parsed is None or routing_result is None:
        engagement = get_engagement(engagement_id, access_token)
        return {
            "engagement_status": engagement.status if engagement else "open",
            "phase": "done",
        }

    decision = routing_result.decision
    if decision is None:
        engagement = get_engagement(engagement_id, access_token)
        return {
            "engagement_status": engagement.status if engagement else "open",
            "phase": "done",
        }

    new_status = _STATUS_BY_ACTION.get(decision.action, "flagged")
    engagement = get_engagement(engagement_id, access_token)

    update_engagement(
        engagement_id,
        access_token=access_token,
        status=new_status,
        response_received=state["response_text"],
        routing_decision=decision.action,
        decision_rationale=decision.rationale,
        ghg_protocol_citation=decision.ghg_protocol_citation,
        next_step=decision.action,
    )
    append_audit_log(
        event="response_parsed_and_routed",
        workflow="parse_response+exception_router",
        user_id=state["user_id"],
        access_token=access_token,
        supplier_name=state["supplier_name"],
        product_name=engagement.product_name if engagement else None,
        component_name=state.get("component")
        or (engagement.component_name if engagement else None),
        email_sent=engagement.email_draft if engagement else None,
        response_received=state["response_text"],
        routing_decision=decision.action,
        decision_rationale=decision.rationale,
        ghg_protocol_citation=decision.ghg_protocol_citation,
        data_collected=parse_result.parsed.data_provided,
        status=new_status,
    )
    return {"engagement_status": new_status, "phase": "routed"}


def _route_after_route_response(state: ResponseRoutingState) -> str:
    routing_result = state.get("routing_result")
    if routing_result is None or routing_result.decision is None:
        return "done"
    if state.get("auto_apply"):
        return "apply_routing"
    return "human_review_route"


def _route_after_human_review_route(state: ResponseRoutingState) -> str:
    if state.get("route_approved") or state.get("auto_apply"):
        return "apply_routing"
    return "done"


def _build_email_draft_graph():
    builder = StateGraph(EmailDraftState)
    builder.add_node("select_supplier", _select_supplier_node)
    builder.add_node("draft_email", _draft_email_node)
    builder.add_node("human_review_email", _human_review_email_node)
    builder.add_node("send_email", _send_email_node)

    builder.add_edge(START, "select_supplier")
    builder.add_edge("select_supplier", "draft_email")
    builder.add_edge("draft_email", "human_review_email")
    builder.add_conditional_edges(
        "human_review_email",
        _route_after_send,
        {"send_email": "send_email", "done": END},
    )
    builder.add_edge("send_email", END)

    return builder.compile(
        checkpointer=get_checkpointer(),
        interrupt_before=["human_review_email"],
    )


def _route_after_process(state: ResponseRoutingState) -> str:
    parse_result = state.get("parse_result")
    if parse_result and parse_result.error:
        return "done"
    return "route_response"


def _build_response_routing_graph():
    builder = StateGraph(ResponseRoutingState)
    builder.add_node("process_response", _process_response_node)
    builder.add_node("route_response", _route_response_node)
    builder.add_node("human_review_route", _human_review_route_node)
    builder.add_node("apply_routing", _apply_routing_node)

    builder.add_edge(START, "process_response")
    builder.add_conditional_edges(
        "process_response",
        _route_after_process,
        {"route_response": "route_response", "done": END},
    )
    builder.add_conditional_edges(
        "route_response",
        _route_after_route_response,
        {
            "apply_routing": "apply_routing",
            "human_review_route": "human_review_route",
            "done": END,
        },
    )
    builder.add_conditional_edges(
        "human_review_route",
        _route_after_human_review_route,
        {"apply_routing": "apply_routing", "done": END},
    )
    builder.add_edge("apply_routing", END)

    return builder.compile(
        checkpointer=get_checkpointer(),
        interrupt_before=["human_review_route"],
    )


_email_draft_graph = None
_response_routing_graph = None


def get_email_draft_graph():
    global _email_draft_graph
    if _email_draft_graph is None:
        _email_draft_graph = _build_email_draft_graph()
    return _email_draft_graph


def get_response_routing_graph():
    global _response_routing_graph
    if _response_routing_graph is None:
        _response_routing_graph = _build_response_routing_graph()
    return _response_routing_graph


def start_email_draft(
    session_id: str,
    product_name: str,
    candidate: EngagementCandidate,
    *,
    user_id: str,
    access_token: str,
) -> EmailDraftState:
    """Draft a supplier email and pause at the human review checkpoint."""
    graph = get_email_draft_graph()
    initial: EmailDraftState = {
        "session_id": session_id,
        "user_id": user_id,
        "access_token": access_token,
        "product_name": product_name,
        "candidate": candidate,
        "suppliers_result": None,
        "email_draft_result": None,
        "phase": "drafting",
        "email_approved": False,
        "email_body": None,
        "engagement_id": None,
    }
    return invoke_graph(graph, session_id, initial)


def approve_and_send_email(
    session_id: str,
    email_body: str | None = None,
) -> EmailDraftState:
    """Resume the email draft graph after human approval and create the engagement."""
    graph = get_email_draft_graph()
    update_graph_state(
        graph,
        session_id,
        {"email_approved": True, "email_body": email_body},
    )
    return invoke_graph(graph, session_id, None)


def get_email_draft_state(session_id: str) -> EmailDraftState | None:
    return get_graph_values(get_email_draft_graph(), session_id)


def start_response_routing(
    session_id: str,
    *,
    engagement_id: int,
    supplier_name: str,
    response_text: str,
    component: str | None = None,
    days_since_contact: int = 0,
    auto_apply: bool = True,
    user_id: str,
    access_token: str,
) -> ResponseRoutingState:
    """Parse and route a supplier response; auto-applies routing when auto_apply=True."""
    graph = get_response_routing_graph()
    thread_id = f"route-{session_id}-{engagement_id}"
    initial: ResponseRoutingState = {
        "session_id": session_id,
        "user_id": user_id,
        "access_token": access_token,
        "engagement_id": engagement_id,
        "supplier_name": supplier_name,
        "component": component,
        "response_text": response_text,
        "days_since_contact": days_since_contact,
        "parse_result": None,
        "routing_result": None,
        "phase": "processing",
        "auto_apply": auto_apply,
        "route_approved": False,
        "engagement_status": None,
    }
    return invoke_graph(graph, thread_id, initial)


def approve_response_routing(
    session_id: str,
    engagement_id: int,
) -> ResponseRoutingState:
    """Resume routing graph after human review of the routing decision."""
    graph = get_response_routing_graph()
    thread_id = f"route-{session_id}-{engagement_id}"
    update_graph_state(graph, thread_id, {"route_approved": True})
    return invoke_graph(graph, thread_id, None)


def get_response_routing_state(
    session_id: str,
    engagement_id: int,
) -> ResponseRoutingState | None:
    return get_graph_values(get_response_routing_graph(), f"route-{session_id}-{engagement_id}")
