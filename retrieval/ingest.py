"""Load Markdown sample documents and write chunks to a selected index."""

import json
import os
import re
from pathlib import Path
from typing import Protocol

from models.documents import DocumentChunk, DocumentRecord
from retrieval.chunking import chunk_document
from retrieval.embeddings import embed_texts

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample_docs"
LOCAL_INDEX = ROOT / "data" / "local_index.jsonl"


class VectorSink(Protocol):
    def upsert(self, chunks: list[DocumentChunk], vectors: list[list[float]]) -> int: ...


def _field(text: str, name: str, default: str) -> str:
    match = re.search(rf"^{re.escape(name)}:\s*(.+)$", text, flags=re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else default


def load_markdown(path: Path) -> DocumentRecord:
    raw = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", raw, flags=re.MULTILINE)
    return DocumentRecord(
        document_id=_field(raw, "Document ID", path.stem.upper()),
        title=title_match.group(1).strip() if title_match else path.stem.replace("_", " ").title(),
        text=raw,
        department=_field(raw, "Department", "general").lower(),
        document_type=_field(raw, "Type", "reference").lower(),
        access_level=_field(raw, "Access", "internal").lower(),
        created_date=_field(raw, "Created", "") or None,
    )


def load_documents(directory: Path = SAMPLE_DIR) -> list[DocumentRecord]:
    return [load_markdown(path) for path in sorted(directory.glob("*.md"))]


def ingest_local(chunks: list[DocumentChunk], vectors: list[list[float]], path: Path = LOCAL_INDEX) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for chunk, vector in zip(chunks, vectors, strict=True):
            record = {"id": chunk.chunk_id, "values": vector, "metadata": chunk.metadata()}
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(chunks)


class PineconeSink:
    def __init__(self) -> None:
        try:
            from pinecone import Pinecone
        except ImportError as exc:
            raise RuntimeError("Install the 'pinecone' package to use Pinecone") from exc
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise RuntimeError("PINECONE_API_KEY is required for Pinecone ingestion")
        self.index_name = os.getenv("PINECONE_INDEX", "jerry-demo")
        self.namespace = os.getenv("PINECONE_NAMESPACE", "jerry-demo")
        self.index = Pinecone(api_key=api_key).Index(self.index_name)

    def upsert(self, chunks: list[DocumentChunk], vectors: list[list[float]]) -> int:
        records = [
            {"id": chunk.chunk_id, "values": vector, "metadata": chunk.metadata()}
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        self.index.upsert(vectors=records, namespace=self.namespace)
        return len(records)


def ingest_sample_data(
    directory: Path = SAMPLE_DIR,
    backend: str = "local",
    chunk_size: int = 900,
    overlap: int = 120,
) -> dict[str, int | str]:
    documents = load_documents(directory)
    if not documents:
        raise ValueError(f"No Markdown documents found in {directory}")
    chunks = [chunk for document in documents for chunk in chunk_document(document, chunk_size, overlap)]
    vectors = embed_texts([chunk.text for chunk in chunks])
    if backend == "local":
        stored = ingest_local(chunks, vectors)
        location = str(LOCAL_INDEX)
    elif backend == "pinecone":
        stored = PineconeSink().upsert(chunks, vectors)
        location = f"{os.getenv('PINECONE_INDEX', 'jerry-demo')}:{os.getenv('PINECONE_NAMESPACE', 'jerry-demo')}"
    else:
        raise ValueError("backend must be 'local' or 'pinecone'")
    return {"documents": len(documents), "chunks": len(chunks), "stored": stored, "backend": backend, "location": location}

