"""Intent routing for knowledge, analysis, and enterprise tool requests."""

import re

ANALYSIS_HINTS = (
    "summarize all", "summarize .* incidents", "recurring", "compare incidents",
    "across incidents", "trend", "root cause", "root causes", "identify causes",
)


def route_request(query: str) -> str:
    normalized = query.casefold()
    if any(term in normalized for term in ("employee directory", "employee lookup", "who works", "find employee", "staff directory")):
        return "mcp_employees"
    if any(term in normalized for term in ("service catalog", "service owner", "who owns", "service tier", "service details")):
        return "mcp_services"
    if any(re.search(hint, normalized) for hint in ANALYSIS_HINTS):
        return "analysis"
    return "knowledge_search"
