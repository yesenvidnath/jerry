"""Document and indexed chunk schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class DocumentRecord(BaseModel):
    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    department: str = "general"
    document_type: str = "reference"
    access_level: Literal["public", "internal", "confidential"] = "internal"
    created_date: date | None = None


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    text: str
    chunk_index: int = Field(ge=0)
    department: str
    document_type: str
    access_level: str
    created_date: date | None = None

    def metadata(self) -> dict[str, str | int | list[float]]:
        """Return Pinecone-safe scalar metadata plus source attribution."""
        values: dict[str, str | int | list[float]] = {
            "document_id": self.document_id,
            "title": self.title,
            "text": self.text,
            "chunk_index": self.chunk_index,
            "department": self.department,
            "document_type": self.document_type,
            "access_level": self.access_level,
        }
        if self.created_date:
            values["created_date"] = self.created_date.isoformat()
        return values
