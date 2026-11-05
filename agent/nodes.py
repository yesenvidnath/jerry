"""LangGraph node implementations for the grounded assistant flow."""

import logging
import os
import re
from typing import Any

from agent.memory import contextualize_query, format_recent_history
from agent.prompts import SYSTEM_PROMPT, USER_PROMPT
from agent.routing import route_request
from models.retrieval import RetrievalFilters
from tools.knowledge_search import search_knowledge
from tools.mcp_client import list_employees, list_services
from tools.permissions import PermissionDenied

logger = logging.getLogger(__name__)
SOURCE_PATTERN = re.compile(r"\[source:([^\]]+)\]")


def _event(state: dict[str, Any], node: str, status: str, detail: str = "") -> list[dict[str, str]]:
    events = list(state.get("activity", []))
    events.append({"node": node, "status": status, "detail": detail})
    return events


def validate_request(state: dict[str, Any]) -> dict[str, Any]:
    query = str(state.get("query", "")).strip()
    events = _event(state, "validate_request", "complete")
    if not query:
        return {"query": "", "errors": ["Question is required."], "answer": "Please enter a question.", "activity": events}
    if len(query) > 4000:
        return {"errors": ["Question exceeds the 4,000 character limit."], "answer": "Please shorten your question.", "activity": events}
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
        return {
            "retrieved": serialized,
            "activity": _event(state, "retrieve", "complete", f"Retrieved {len(serialized)} passages using current question and recent context"),
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
    sufficient = bool(passages) and max(
        (float(item.get("dense_score", 0)) + float(item.get("sparse_score", 0)) for item in passages),
        default=0,
    ) > 0
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
        f"[source:{item['document_id']}] {item['title']}\n{item['passage']}"
        for item in passages[:8]
    )
    provider = os.getenv("LLM_PROVIDER", "local").lower()
    if provider == "openai":
        try:
            from langchain_openai import ChatOpenAI
            model = ChatOpenAI(model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"), temperature=0)
            message = await model.ainvoke([
                ("system", SYSTEM_PROMPT),
                ("human", USER_PROMPT.format(
                    query=state["query"], evidence=evidence,
                    conversation_context=format_recent_history(state.get("recent_history", [])),
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
    allowed = {str(item.get("document_id")) for item in state.get("retrieved", [])}
    used = set(SOURCE_PATTERN.findall(state.get("answer", "")))
    invalid = used - allowed
    answer = state.get("answer", "")
    if invalid:
        answer = re.sub(r"\s*\[source:[^\]]+\]", "", answer)
        answer += "\n\nI could not validate one or more generated citations, so I removed them."
    citations = []
    seen = set()
    for item in state.get("retrieved", []):
        doc_id = str(item.get("document_id", ""))
        if doc_id in used and doc_id not in seen:
            seen.add(doc_id)
            citations.append({"document_id": doc_id, "title": str(item.get("title", "")), "chunk_id": str(item.get("chunk_id", ""))})
    return {
        "answer": answer,
        "citations": citations,
        "activity": _event(state, "validate_citations", "complete", f"Validated {len(citations)} source(s)"),
    }


async def invoke_mcp_tool(state: dict[str, Any]) -> dict[str, Any]:
    import asyncio
    route = state.get("route")
    try:
        if route == "mcp_employees":
            records = await asyncio.to_thread(list_employees, state.get("role", "Viewer"))
            lines = [f"- {person['name']} — {person['title']} ({person['department']})" for person in records]
            answer = "Employee directory results:\n" + "\n".join(lines)
            detail = f"Retrieved {len(records)} employee record(s)"
        else:
            records = await asyncio.to_thread(list_services, state.get("role", "Viewer"))
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
