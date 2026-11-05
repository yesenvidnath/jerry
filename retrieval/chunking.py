"""Deterministic text chunking with a configurable overlap."""

from models.documents import DocumentChunk, DocumentRecord


def split_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    normalized = " ".join(text.split())
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start + chunk_size // 2, end)
            if boundary > start:
                end = boundary
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_document(
    document: DocumentRecord, chunk_size: int = 900, overlap: int = 120
) -> list[DocumentChunk]:
    return [
        DocumentChunk(
            chunk_id=f"{document.document_id}:{index}",
            document_id=document.document_id,
            title=document.title,
            text=text,
            chunk_index=index,
            department=document.department,
            document_type=document.document_type,
            access_level=document.access_level,
            created_date=document.created_date,
        )
        for index, text in enumerate(split_text(document.text, chunk_size, overlap))
    ]
