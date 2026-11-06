"""Tool API schemas."""

from pydantic import BaseModel, Field


class AnalysisPassage(BaseModel):
    document_id: str = Field(min_length=1, max_length=120)
    title: str = Field(default="", max_length=300)
    chunk_id: str = Field(default="", max_length=160)
    passage: str = Field(min_length=1, max_length=3000)


class AnalysisToolRequest(BaseModel):
    passages: list[AnalysisPassage] = Field(min_length=1, max_length=12)


class SearchToolRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    department: str | None = Field(default=None, max_length=80)
    document_type: str | None = Field(default=None, max_length=80)
