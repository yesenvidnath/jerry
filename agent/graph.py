"""Construct and compile the bounded LangGraph assistant workflow."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from agent.nodes import check_evidence, respond, retrieve, supervisor, validate_citations, validate_request
from agent.rlm import aggregate_analysis, analyze_batches, plan_analysis, retrieve_analysis_documents
from models.state import AssistantState


def _after_validation(state: AssistantState) -> str:
    return END if state.get("errors") and state.get("answer") else "supervisor"


def _route_after_supervisor(state: AssistantState) -> str:
    return "plan_analysis" if state.get("route") == "analysis" else "retrieve"


def _after_evidence(state: AssistantState) -> str:
    if state.get("evidence_sufficient"):
        return "respond"
    if state.get("retry_count", 0) < state.get("max_retries", 1):
        return "retry_retrieval"
    return "respond"


def _retry_retrieval(state: AssistantState) -> dict[str, Any]:
    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "activity": list(state.get("activity", [])) + [{
            "node": "retry_retrieval", "status": "complete", "detail": "One bounded wider search retry"
        }],
    }


def build_graph():
    graph = StateGraph(AssistantState)
    graph.add_node("validate_request", validate_request)
    graph.add_node("supervisor", supervisor)
    graph.add_node("retrieve", retrieve)
    graph.add_node("check_evidence", check_evidence)
    graph.add_node("retry_retrieval", _retry_retrieval)
    graph.add_node("respond", respond)
    graph.add_node("validate_citations", validate_citations)
    graph.add_node("plan_analysis", plan_analysis)
    graph.add_node("retrieve_analysis_documents", retrieve_analysis_documents)
    graph.add_node("analyze_batches", analyze_batches)
    graph.add_node("aggregate_analysis", aggregate_analysis)

    graph.add_edge(START, "validate_request")
    graph.add_conditional_edges("validate_request", _after_validation, {END: END, "supervisor": "supervisor"})
    graph.add_conditional_edges("supervisor", _route_after_supervisor, {
        "retrieve": "retrieve", "plan_analysis": "plan_analysis"
    })
    graph.add_edge("retrieve", "check_evidence")
    graph.add_conditional_edges("check_evidence", _after_evidence, {
        "respond": "respond", "retry_retrieval": "retry_retrieval"
    })
    graph.add_edge("retry_retrieval", "retrieve")
    graph.add_edge("respond", "validate_citations")
    graph.add_edge("plan_analysis", "retrieve_analysis_documents")
    graph.add_edge("retrieve_analysis_documents", "analyze_batches")
    graph.add_edge("analyze_batches", "aggregate_analysis")
    graph.add_edge("aggregate_analysis", "validate_citations")
    graph.add_edge("validate_citations", END)
    return graph.compile()


assistant_graph = build_graph()
