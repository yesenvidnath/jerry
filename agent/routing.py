"""Simple, deterministic intent routing for the first assistant stage."""

ANALYSIS_HINTS = ("summarize all", "recurring", "compare incidents", "across incidents", "trend")


def route_request(query: str) -> str:
    normalized = query.casefold()
    return "analysis" if any(hint in normalized for hint in ANALYSIS_HINTS) else "knowledge_search"
