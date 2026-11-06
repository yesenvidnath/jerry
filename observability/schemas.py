"""Timestamped graph activity and LangSmith trace references."""

from pydantic import BaseModel, Field


class ActivityEvent(BaseModel):
    node: str
    status: str
    detail: str = ""
    timestamp: str | None = None


class TraceReference(BaseModel):
    trace_id: str
    project_name: str | None = None
    tracing_enabled: bool = False
