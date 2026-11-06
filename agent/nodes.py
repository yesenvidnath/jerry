"""LangGraph node implementations for the grounded assistant flow."""

import logging
import os
from typing import Any

from agent.memory import contextualize_query, format_recent_history
from core.config import settings
from agent.prompts import SYSTEM_PROMPT, USER_PROMPT
from agent.routing import route_request
from models.retrieval import RetrievalFilters
from tools.knowledge_search import search_knowledge
from tools.mcp_client import list_employees, list_services
from tools.permissions import PermissionDenied
from security.guardrails import inspect_untrusted_text, redact_unsafe_output, reject_unsafe_request, validate_citations as check_citations
from security.validation import UnsafeInput, validate_retrieved_passages, validate_user_query
from observability.events import make_activity_event

logger = logging.getLogger(__name__)


def _event(state: dict[str, Any], node: str, status: str, detail: str = "") -> list[dict[str, str]]:
    events = list(state.get("activity", []))
    events.append(make_activity_event(node, status, detail))
    return events


def validate_request(state: dict[str, Any]) -> dict[str, Any]:
    query = str(state.get("query", ""))
    events = _event(state, "validate_request", "complete")
    try:
        query = validate_user_query(query)
    except UnsafeInput as exc:
        return {"query": query, "errors": [str(exc)], "answer": "Please enter a valid question without unsupported control characters.", "activity": _event(state, "validate_request", "rejected", str(exc))}
    refusal = reject_unsafe_request(query)
    if refusal:
        return {"query": query, "errors": ["Request rejected by security guardrail."], "answer": refusal, "activity": _event(state, "guardrail", "blocked", "Unsafe request pattern detected")}
    return {"query": query, "activity": events, "errors": []}


def supervisor(state: dict[str, Any]) -> dict[str, Any]:
    route = route_request(state["query"])
    detail = f"Selected {route}"
    if state.get("recent_history"):
        detail += f"; using {len(state['recent_history'])} recent memory turn(s)"
    return {"route": route, "activity": _event(state, "supervisor", "complete", detail)}


async def retrieve(state: dict[str, Any]) -> dict[str, Any]:
    try:
        limit = 5 if state.get("retry_count", 0) == 0 else 10
        search_query = contextualize_query(state["query"], state.get("recent_history", []))
        results = await search_knowledge(search_query, state.get("role", "Viewer"), top_k=limit, filters=RetrievalFilters())
        serialized = [item.model_dump(mode="json") for item in results]
        safe_passages, rejected = validate_retrieved_passages(serialized)
        detail = f"Retrieved {len(safe_passages)} validated passages"
        if rejected:
            detail += f"; dropped {len(rejected)} unsafe or malformed passage(s)"
        return {
            "retrieved": safe_passages,
            "activity": _event(state, "retrieve", "complete", detail),
        }
    except Exception as exc:
        logger.exception("retrieval_failed")
        return {
            "retrieved": [],
            "errors": list(state.get("errors", [])) + [f"Retrieval failed: {type(exc).__name__}"],
            "activity": _event(state, "retrieve", "failed", "Knowledge search was unavailable"),
        }


def check_evidence(state: dict[str, Any]) -> dict[str, Any]:
    passages = state.get("retrieved", [])
    semantic_embeddings = os.getenv("EMBEDDING_PROVIDER", "local").lower() != "local"
    sufficient = any(
        float(item.get("sparse_score", 0)) > 0
        or (semantic_embeddings and float(item.get("dense_score", 0)) >= 0.2)
        for item in passages
    )
    events = _event(state, "check_evidence", "complete", "Evidence found" if sufficient else "No matching evidence")
    return {"evidence_sufficient": sufficient, "activity": events}


def _fallback_answer(query: str, passages: list[dict[str, Any]]) -> str:
    if not passages:
        return "I couldn't find supporting information in the indexed documents, so I can't answer this reliably."
    selected = passages[:3]
    lines = ["Here is what the indexed material says:"]
    for item in selected:
        excerpt = str(item.get("passage", "")).strip()
        excerpt = excerpt[:550].rstrip()
        doc_id = item.get("document_id", "unknown")
        lines.append(f"- {excerpt} [source:{doc_id}]")
    return "\n".join(lines)


async def respond(state: dict[str, Any]) -> dict[str, Any]:
    passages = state.get("retrieved", [])
    if not state.get("evidence_sufficient"):
        answer = "I couldn't find supporting information in the indexed documents, so I can't answer this reliably."
        return {"answer": answer, "activity": _event(state, "respond", "complete", "Returned safe no-evidence response")}

    evidence = "\n\n".join(
        f"<untrusted_evidence source_id=\"{item['document_id']}\" title=\"{item['title']}\">\n{item['passage']}\n</untrusted_evidence>"
        for item in passages[:8]
    )
    safe_history = [
        turn for turn in state.get("recent_history", [])
        if not inspect_untrusted_text(str(turn.get("content", "")))
    ]
    provider = os.getenv("LLM_PROVIDER", "local").lower()
    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
            model = ChatOpenAI(model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"), temperature=0, timeout=settings.llm_timeout_seconds)
            message = await model.ainvoke([
                ("system", SYSTEM_PROMPT),
                ("human", USER_PROMPT.format(
                    query=state["query"], evidence=evidence,
                    conversation_context=format_recent_history(safe_history),
                )),
            ])
            answer = str(message.content)
        except Exception as exc:
            logger.exception("llm_response_failed")
            return {
                "answer": _fallback_answer(state["query"], passages),
                "errors": list(state.get("errors", [])) + [f"LLM unavailable: {type(exc).__name__}"],
                "activity": _event(state, "respond", "degraded", "Used extractive response fallback"),
            }
    else:
        answer = _fallback_answer(state["query"], passages)
    return {"answer": answer, "activity": _event(state, "respond", "complete", "Answer generated from retrieved evidence")}


def validate_citations(state: dict[str, Any]) -> dict[str, Any]:
    passages = state.get("retrieved", [])
    answer = str(state.get("answer", ""))
    answer, redacted = redact_unsafe_output(answer)
    answer, used, invalid = check_citations(answer, passages)
    if passages and not used and state.get("evidence_sufficient"):
        answer = _fallback_answer(state.get("query", ""), passages)
        answer, redacted = redact_unsafe_output(answer)
        answer, used, invalid_again = check_citations(answer, passages)
        invalid = invalid or invalid_again
    citations = []
    seen = set()
    for item in passages:
        doc_id = str(item.get("document_id", ""))
        if doc_id in used and doc_id not in seen:
            seen.add(doc_id)
            citations.append({"document_id": doc_id, "title": str(item.get("title", "")), "chunk_id": str(item.get("chunk_id", ""))})
    detail = f"Validated {len(citations)} source(s)"
    if invalid:
        detail += "; removed invalid citations"
    if redacted:
        detail += "; redacted unsafe output or enforced output length limit"
    return {
        "answer": answer,
        "citations": citations,
        "activity": _event(state, "validate_citations", "complete", detail),
    }


async def invoke_mcp_tool(state: dict[str, Any]) -> dict[str, Any]:
    import asyncio
    route = state.get("route")
    try:
        if route == "mcp_employees":
            records = await asyncio.wait_for(asyncio.to_thread(list_employees, state.get("role", "Viewer")), timeout=settings.tool_timeout_seconds)
            lines = [f"- {person['name']} — {person['title']} ({person['department']})" for person in records]
            answer = "Employee directory results:\n" + "\n".join(lines)
            detail = f"Retrieved {len(records)} employee record(s)"
        else:
            records = await asyncio.wait_for(asyncio.to_thread(list_services, state.get("role", "Viewer")), timeout=settings.tool_timeout_seconds)
            lines = [f"- {item['name']} — owner: {item['owner']}; tier: {item['tier']}" for item in records]
            answer = "Service catalog results:\n" + "\n".join(lines)
            detail = f"Retrieved {len(records)} service record(s)"
        return {"tool_results": records, "answer": answer, "activity": _event(state, "mcp_tool", "complete", detail)}
    except PermissionDenied as exc:
        return {
            "answer": "This request needs the Analyst role or Administrator role to use the enterprise data tool.",
            "errors": list(state.get("errors", [])) + [str(exc)],
            "activity": _event(state, "authorize_tool", "denied", str(exc)),
        }
    except TimeoutError:
        return {
            "answer": "The enterprise data tool timed out. Please try again shortly.",
            "errors": list(state.get("errors", [])) + ["MCP tool timeout"],
            "activity": _event(state, "mcp_tool", "failed", "Tool execution exceeded its configured timeout"),
        }
    except Exception as exc:
        logger.exception("mcp_tool_failed")
        return {
            "answer": "The enterprise data tool is temporarily unavailable.",
            "errors": list(state.get("errors", [])) + [f"MCP tool failed: {type(exc).__name__}"],
            "activity": _event(state, "mcp_tool", "failed", "Tool execution failed safely"),
        }



def deny_mcp(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "answer": "This enterprise directory/catalog tool requires the Analyst role or Administrator role.",
        "errors": list(state.get("errors", [])) + ["Permission denied: mcp_tools"],
        "activity": _event(state, "authorize_tool", "denied", "Viewer cannot run MCP tools"),
    }

def deny_analysis(state: dict[str, Any]) -> dict[str, Any]:
    answer = "This request needs the Analyst role because it runs the Python analysis tool. You can still ask a regular knowledge-search question."
    return {
        "answer": answer,
        "errors": list(state.get("errors", [])) + ["Permission denied: python_analysis"],
        "activity": _event(state, "authorize_tool", "denied", "Viewer cannot run analytics tools"),
    }
