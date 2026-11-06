"""Typed state carried through the assistant graph."""

from typing import Any, TypedDict


class AssistantState(TypedDict, total=False):
    query: str
    role: str
    session_id: str
    route: str
    retrieved: list[dict[str, Any]]
    evidence_sufficient: bool
    answer: str
    citations: list[dict[str, str]]
    activity: list[dict[str, str]]
    errors: list[str]
    retry_count: int
    max_retries: int
    rlm_plan: dict[str, Any]
    batch_results: list[dict[str, Any]]
    analysis_summary: dict[str, Any]
