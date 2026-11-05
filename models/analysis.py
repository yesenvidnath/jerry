"""Schemas for bounded recursive document analysis."""

from typing import TypedDict, Any


class AnalysisPlan(TypedDict):
    topic_query: str
    document_type: str
    department: str | None
    created_after: str | None
    created_before: str | None
    batch_size: int
    max_batches: int


class BatchFinding(TypedDict):
    batch_number: int
    documents_examined: list[str]
    key_findings: list[str]
    cause_counts: dict[str, int]
    citations: list[dict[str, str]]
    passage_count: int
