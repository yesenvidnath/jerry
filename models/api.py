"""Assistant chat request and response schemas."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(default="demo", min_length=1, max_length=120)


class Citation(BaseModel):
    document_id: str
    title: str
    chunk_id: str


class ActivityEvent(BaseModel):
    node: str
    status: str
    detail: str = ""
    timestamp: str | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    activity: list[ActivityEvent] = Field(default_factory=list)
    error: str | None = None
    memory_turns: int = 0
    trace_id: str | None = None
    tracing_enabled: bool = False
    trace_project: str | None = None
