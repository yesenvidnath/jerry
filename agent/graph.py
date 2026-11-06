"""Construct and compile the bounded LangGraph assistant workflow."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from agent.nodes import check_evidence, deny_analysis, deny_mcp, invoke_mcp_tool, respond, retrieve, supervisor, validate_citations, validate_request
from agent.rlm import aggregate_analysis, analyze_batches, plan_analysis, retrieve_analysis_documents
from models.state import AssistantState
from observability.events import make_activity_event


def _after_validation(state: AssistantState) -> str:
    return END if state.get("errors") and state.get("answer") else "supervisor"


def _route_after_supervisor(state: AssistantState) -> str:
    role = state.get("role")
    route = state.get("route")
    if route == "analysis":
        return "plan_analysis" if role in {"Analyst", "Administrator"} else "deny_analysis"
    if route in {"mcp_employees", "mcp_services"}:
        return "invoke_mcp_tool" if role in {"Analyst", "Administrator"} else "deny_mcp"
    return "retrieve"


def _after_evidence(state: AssistantState) -> str:
    if state.get("evidence_sufficient"):
        return "respond"
    if state.get("retry_count", 0) < state.get("max_retries", 1):
        return "retry_retrieval"
    return "respond"


def _retry_retrieval(state: AssistantState) -> dict[str, Any]:
    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "activity": list(state.get("activity", [])) + [
            make_activity_event("retry_retrieval", "complete", "One bounded wider search retry")
        ],
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
    graph.add_node("deny_analysis", deny_analysis)
    graph.add_node("deny_mcp", deny_mcp)
    graph.add_node("invoke_mcp_tool", invoke_mcp_tool)
    graph.add_node("plan_analysis", plan_analysis)
    graph.add_node("retrieve_analysis_documents", retrieve_analysis_documents)
    graph.add_node("analyze_batches", analyze_batches)
    graph.add_node("aggregate_analysis", aggregate_analysis)

    graph.add_edge(START, "validate_request")
    graph.add_conditional_edges("validate_request", _after_validation, {END: END, "supervisor": "supervisor"})
    graph.add_conditional_edges("supervisor", _route_after_supervisor, {
        "retrieve": "retrieve", "plan_analysis": "plan_analysis", "deny_analysis": "deny_analysis",
        "invoke_mcp_tool": "invoke_mcp_tool", "deny_mcp": "deny_mcp",
    })
    graph.add_edge("retrieve", "check_evidence")
    graph.add_conditional_edges("check_evidence", _after_evidence, {
        "respond": "respond", "retry_retrieval": "retry_retrieval"
    })
    graph.add_edge("retry_retrieval", "retrieve")
    graph.add_edge("respond", "validate_citations")
    graph.add_edge("deny_analysis", END)
    graph.add_edge("deny_mcp", END)
    graph.add_edge("invoke_mcp_tool", END)
    graph.add_edge("plan_analysis", "retrieve_analysis_documents")
    graph.add_edge("retrieve_analysis_documents", "analyze_batches")
    graph.add_edge("analyze_batches", "aggregate_analysis")
    graph.add_edge("aggregate_analysis", "validate_citations")
    graph.add_edge("validate_citations", END)
    return graph.compile()


assistant_graph = build_graph()
