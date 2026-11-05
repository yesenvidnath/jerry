"""Dense retrieval over the local index or configured Pinecone namespace."""

import json
import os
from pathlib import Path

from models.retrieval import RetrievalFilters, SearchResult
from retrieval.embeddings import embed_texts
from retrieval.ingest import LOCAL_INDEX


def _matches(metadata: dict, filters: RetrievalFilters | None) -> bool:
    if not filters:
        return True
    for field in ("department", "document_type", "access_level"):
        expected = getattr(filters, field)
        if expected and str(metadata.get(field, "")).lower() != expected.lower():
            return False
    created = metadata.get("created_date")
    if filters.created_after and (not created or created < filters.created_after.isoformat()):
        return False
    if filters.created_before and (not created or created > filters.created_before.isoformat()):
        return False
    return True


def _pinecone_filter(filters: RetrievalFilters | None) -> dict | None:
    if not filters:
        return None
    result = {}
    for field in ("department", "document_type", "access_level"):
        expected = getattr(filters, field)
        if expected:
            result[field] = {"$eq": expected.lower()}
    if filters.created_after:
        result["created_date"] = {"$gte": filters.created_after.isoformat()}
    if filters.created_before:
        if "created_date" in result:
            result["created_date"]["$lte"] = filters.created_before.isoformat()
        else:
            result["created_date"] = {"$lte": filters.created_before.isoformat()}
    return result or None


def dense_search(
    query: str,
    top_k: int = 5,
    filters: RetrievalFilters | None = None,
    index_path: Path = LOCAL_INDEX,
) -> list[SearchResult]:
    query_vector = embed_texts([query])[0]
    if os.getenv("VECTOR_BACKEND", "local").lower() == "pinecone":
        try:
            from pinecone import Pinecone
        except ImportError as exc:
            raise RuntimeError("Install the 'pinecone' package to search Pinecone") from exc
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise RuntimeError("PINECONE_API_KEY is required for Pinecone retrieval")
        index = Pinecone(api_key=api_key).Index(os.getenv("PINECONE_INDEX", "jerry-demo"))
        response = index.query(
            vector=query_vector,
            top_k=top_k,
            namespace=os.getenv("PINECONE_NAMESPACE", "jerry-demo"),
            include_metadata=True,
            filter=_pinecone_filter(filters),
        )
        results = []
        for rank, match in enumerate(response.matches, start=1):
            meta = dict(match.metadata or {})
            results.append(SearchResult(
                chunk_id=match.id, document_id=meta.get("document_id", ""),
                title=meta.get("title", ""), passage=meta.get("text", ""),
                department=meta.get("department", "general"),
                document_type=meta.get("document_type", "reference"),
                access_level=meta.get("access_level", "internal"),
                created_date=meta.get("created_date"), dense_score=float(match.score or 0), rank=rank,
            ))
        return results

    if not index_path.exists():
        raise FileNotFoundError("Local index is missing. Run scripts/ingest_sample_data.py first.")
    scored: list[tuple[float, dict]] = []
    with index_path.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            record = json.loads(line)
            metadata = record.get("metadata", {})
            if not _matches(metadata, filters):
                continue
            values = record.get("values", [])
            if len(values) != len(query_vector):
                raise ValueError("Query and indexed vectors have different dimensions")
            score = sum(a * b for a, b in zip(query_vector, values))
            scored.append((score, record))
    scored.sort(key=lambda item: item[0], reverse=True)
    results = []
    for rank, (score, record) in enumerate(scored[:top_k], start=1):
        meta = record["metadata"]
        results.append(SearchResult(
            chunk_id=record["id"], document_id=meta["document_id"], title=meta["title"],
            passage=meta["text"], department=meta["department"],
            document_type=meta["document_type"], access_level=meta["access_level"],
            created_date=meta.get("created_date"), dense_score=score, rank=rank,
        ))
    return results
