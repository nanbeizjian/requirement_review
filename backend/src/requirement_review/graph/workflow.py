from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from requirement_review.domain.models import ReviewDimension
from requirement_review.graph.state import ReviewState
from requirement_review.review.nodes import ReviewServices


def route_reviews(state: ReviewState) -> list[Send] | str:
    if state["status"] == "FAILED":
        return END
    return [
        Send("review_dimension", {**state, "active_dimension": dimension})
        for dimension in state["selected_dimensions"]
    ]


def build_review_graph(services: ReviewServices, checkpointer: BaseCheckpointSaver):
    if checkpointer is None:
        raise ValueError("a checkpointer is required for approval recovery")

    def approval_node(state: ReviewState) -> dict:
        payload = {"review_id": state["review_id"], "status": "WAITING_APPROVAL"}
        if approval_error := state.get("approval_error"):
            payload["error"] = approval_error
        return {"pending_approval": interrupt(payload)}

    def validate_approval_node(state: ReviewState) -> dict:
        decision = state["pending_approval"]
        cleared = {"pending_approval": None, "approval_error": None}
        try:
            if not isinstance(decision, dict):
                raise TypeError("invalid decision")
            actor = decision.get("actor_id")
            if not isinstance(actor, str) or not actor.strip():
                raise ValueError("actor required")
            action = decision.get("action")
            if action == "approve":
                return {**cleared, "approval": decision, "status": "COMPLETED"}
            if action == "modify":
                updated = services.modify(state, decision.get("findings"))
                return {
                    **cleared,
                    "approval": decision,
                    "dimension_results": updated,
                    "status": "CONSOLIDATING",
                }
            if action in {"re-review", "reject"}:
                requested = decision.get("dimensions")
                if not isinstance(requested, list) or not requested:
                    raise ValueError("dimensions required")
                dimensions = list(
                    dict.fromkeys(ReviewDimension(item) for item in requested)
                )
                return {
                    **cleared,
                    "approval": decision,
                    "selected_dimensions": dimensions,
                    "status": "REVIEWING",
                }
            raise ValueError("unknown action")
        except (ValueError, TypeError):
            # Leave only a safe summary, then create a fresh waiting task/namespace.
            return {
                **cleared,
                "status": "WAITING_APPROVAL",
                "approval_error": "invalid_approval",
            }

    def route_approval(state: ReviewState) -> str | list[Send]:
        if state["status"] == "COMPLETED":
            return END
        if state["status"] == "CONSOLIDATING":
            return "consolidate"
        if state["status"] == "WAITING_APPROVAL":
            return "approval"
        return route_reviews(state)

    graph = StateGraph(ReviewState)
    graph.add_node("parse", services.parse)
    graph.add_node("retrieve", services.retrieve)
    graph.add_node("review_dimension", services.review_dimension)
    graph.add_node("prepare_consolidation", services.prepare_consolidation)
    graph.add_node("consolidate", services.consolidate)
    graph.add_node("approval", approval_node)
    graph.add_node("validate_approval", validate_approval_node)
    graph.add_edge(START, "parse")
    graph.add_conditional_edges(
        "parse",
        lambda state: END if state["status"] == "FAILED" else "retrieve",
        [END, "retrieve"],
    )
    graph.add_conditional_edges("retrieve", route_reviews, [END, "review_dimension"])
    graph.add_edge("review_dimension", "prepare_consolidation")
    graph.add_conditional_edges(
        "prepare_consolidation",
        lambda state: END if state["status"] == "FAILED" else "consolidate",
        [END, "consolidate"],
    )
    graph.add_edge("consolidate", "approval")
    graph.add_edge("approval", "validate_approval")
    graph.add_conditional_edges(
        "validate_approval",
        route_approval,
        [END, "consolidate", "review_dimension", "approval"],
    )
    return graph.compile(checkpointer=checkpointer)
