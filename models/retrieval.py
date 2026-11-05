"""Stable result schemas returned by retrieval backends."""

from datetime import date
from pydantic import BaseModel, Field


class RetrievalFilters(BaseModel):
    department: str | None = None
    document_type: str | None = None
    access_level: str | None = None
    created_after: date | None = None
    created_before: date | None = None


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    passage: str
    department: str
    document_type: str
    access_level: str
    created_date: date | None = None
    dense_score: float = 0.0
    sparse_score: float = 0.0
    hybrid_score: float = 0.0
    rank: int = Field(ge=1)
