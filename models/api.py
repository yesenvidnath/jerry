"""Assistant API request and response schemas."""

from typing import Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="demo", min_length=1, max_length=120)
    user_id: str = Field(default="demo", min_length=1, max_length=120)
    role: Literal["Viewer", "Analyst", "Administrator"] = "Viewer"


class Citation(BaseModel):
    document_id: str
    title: str
    chunk_id: str


class ActivityEvent(BaseModel):
    node: str
    status: str
    detail: str = ""


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    activity: list[ActivityEvent] = Field(default_factory=list)
    error: str | None = None
    memory_turns: int = 0
