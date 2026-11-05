"""Simple, deterministic intent routing for the first assistant stage."""

ANALYSIS_HINTS = (
    "summarize all", "summarize .* incidents", "recurring", "compare incidents",
    "across incidents", "trend", "root cause", "root causes", "identify causes",
)


def route_request(query: str) -> str:
    import re
    normalized = query.casefold()
    if any(re.search(hint, normalized) for hint in ANALYSIS_HINTS):
        return "analysis"
    return "knowledge_search"
