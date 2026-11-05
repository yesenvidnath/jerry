"""LangGraph nodes for bounded recursive multi-document analysis."""

from datetime import date, timedelta
from typing import Any

from agent.memory import contextualize_query
from models.analysis import AnalysisPlan
from observability.events import make_activity_event
from models.retrieval import RetrievalFilters
from tools.knowledge_search import search_knowledge
from security.validation import validate_retrieved_passages
from tools.analysis import aggregate_findings, analyze_batch, make_batches


def plan_analysis(state: dict[str, Any]) -> dict[str, Any]:
    query = state["query"]
    normalized = query.casefold()
    today = date.today()
    if "last year" in normalized:
        created_after = date(today.year - 1, 1, 1)
        created_before = date(today.year - 1, 12, 31)
    elif "past year" in normalized:
        created_after = today - timedelta(days=365)
        created_before = today
    else:
        created_after = created_before = None
    department = "payments" if "payment" in normalized else None
    plan: AnalysisPlan = {
        "topic_query": contextualize_query(query, state.get("recent_history", [])),
        "document_type": "incident report",
        "department": department,
        "created_after": created_after.isoformat() if created_after else None,
        "created_before": created_before.isoformat() if created_before else None,
        "batch_size": 3,
        "max_batches": 4,
    }
    events = list(state.get("activity", []))
    events.append(make_activity_event("rlm_plan", "complete", "Created a bounded incident search and batch plan"))
    return {"rlm_plan": plan, "activity": events}


async def retrieve_analysis_documents(state: dict[str, Any]) -> dict[str, Any]:
    plan = state["rlm_plan"]
    filters = RetrievalFilters(
        department=plan["department"],
        document_type=plan["document_type"],
        created_after=plan["created_after"],
        created_before=plan["created_before"],
    )
    try:
        retrieved = await search_knowledge(plan["topic_query"], state.get("role", "Viewer"), top_k=plan["batch_size"] * plan["max_batches"], filters=filters)
        raw_passages = [item.model_dump(mode="json") for item in retrieved]
        passages, rejected = validate_retrieved_passages(raw_passages)
        errors = []
        detail = f"Found {len(passages)} validated passages"
        if rejected:
            detail += f"; dropped {len(rejected)} unsafe or malformed passage(s)"
    except Exception as exc:
        passages, errors = [], [f"Analysis retrieval failed: {type(exc).__name__}"]
        detail = "Document search was unavailable"
    events = list(state.get("activity", []))
    events.append(make_activity_event("rlm_search", "complete" if passages else "failed", detail))
    return {"retrieved": passages, "errors": list(state.get("errors", [])) + errors, "activity": events}


def analyze_batches(state: dict[str, Any]) -> dict[str, Any]:
    plan = state["rlm_plan"]
    batches = make_batches(state.get("retrieved", []), plan["batch_size"], plan["max_batches"])
    results = [analyze_batch(index, batch, state.get("role", "Viewer")) for index, batch in enumerate(batches, start=1)]
    events = list(state.get("activity", []))
    for result in results:
        events.append(make_activity_event(
            "rlm_batch_analysis", "complete",
            f"Batch {result['batch_number']}: analyzed {result['passage_count']} passages across {len(result['documents_examined'])} documents",
        ))
    if not results:
        events.append(make_activity_event("rlm_batch_analysis", "complete", "No matching passages to analyze"))
    return {"batch_results": results, "activity": events}


def aggregate_analysis(state: dict[str, Any]) -> dict[str, Any]:
    summary = aggregate_findings(state.get("batch_results", []))
    if not summary["documents_examined"]:
        answer = "I couldn't find matching incident reports in the indexed documents for that topic and date range."
    else:
        lines = [
            f"Reviewed {len(summary['documents_examined'])} incident document(s) in bounded batches.",
            "Recurring cause signals identified:",
        ]
        if summary["cause_counts"]:
            lines.extend(f"- {cause}: observed in {count} passage signal(s)" for cause, count in sorted(summary["cause_counts"].items(), key=lambda pair: (-pair[1], pair[0])))
        else:
            lines.append("- The retrieved reports did not contain a recognized recurring-cause signal.")
        if summary["key_findings"]:
            lines.append("\nSupporting findings:")
            lines.extend(f"- {finding}" for finding in summary["key_findings"][:5])
        lines.append("\nCause categories are deterministic Python text-pattern signals and should be reviewed against the cited reports.")
        lines.append(" ".join(f"[source:{doc_id}]" for doc_id in summary["documents_examined"]))
        answer = "\n".join(lines)
    events = list(state.get("activity", []))
    events.append(make_activity_event("rlm_aggregate", "complete", f"Aggregated {len(state.get('batch_results', []))} bounded batch result(s)"))
    return {"analysis_summary": summary, "answer": answer, "citations": summary["citations"], "activity": events}



