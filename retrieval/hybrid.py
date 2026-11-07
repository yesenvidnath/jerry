"""Explainable hybrid retrieval and asynchronous service interface."""

import asyncio
import os

from models.retrieval import RetrievalFilters, SearchResult
from retrieval.dense import dense_search
from retrieval.sparse import sparse_search


def hybrid_search(
    query: str,
    top_k: int = 5,
    filters: RetrievalFilters | None = None,
    dense_weight: float = 0.55,
    sparse_weight: float = 0.45,
    candidate_k: int | None = None,
) -> list[SearchResult]:
    """Fuse dense and BM25 rankings using weighted reciprocal rank fusion.

    Each path contributes weight / (60 + rank). The constant 60 limits the
    effect of small rank changes; the separate raw scores remain visible.
    """
    if dense_weight < 0 or sparse_weight < 0 or dense_weight + sparse_weight <= 0:
        raise ValueError("Weights must be non-negative and at least one must be positive")
    limit = candidate_k or max(top_k * 3, top_k)
    sparse = sparse_search(query, top_k=limit, filters=filters)
    semantic_embeddings = os.getenv("EMBEDDING_PROVIDER", "local").lower() != "local"
    if semantic_embeddings:
        dense = dense_search(query, top_k=limit, filters=filters)
    else:
        # Feature-hash vectors are deterministic demo features, not semantic
        # embeddings. Do not let their arbitrary collisions outrank BM25 hits.
        dense = []
        dense_weight, sparse_weight = 0.0, 1.0
    merged: dict[str, SearchResult] = {item.chunk_id: item for item in dense}
    sparse_by_id = {item.chunk_id: item for item in sparse}
    for chunk_id, item in sparse_by_id.items():
        if chunk_id not in merged:
            merged[chunk_id] = item
    for chunk_id, item in merged.items():
        dense_item = next((candidate for candidate in dense if candidate.chunk_id == chunk_id), None)
        sparse_item = sparse_by_id.get(chunk_id)
        item.dense_score = dense_item.dense_score if dense_item else 0.0
        item.sparse_score = sparse_item.sparse_score if sparse_item else 0.0
        item.hybrid_score = (
            dense_weight / (60 + dense_item.rank) if dense_item else 0.0
        ) + (
            sparse_weight / (60 + sparse_item.rank) if sparse_item else 0.0
        )
    ranked = sorted(merged.values(), key=lambda item: item.hybrid_score, reverse=True)[:top_k]
    for rank, item in enumerate(ranked, start=1):
        item.rank = rank
    return ranked


async def aretrieve(
    query: str,
    top_k: int = 5,
    filters: RetrievalFilters | None = None,
    dense_weight: float = 0.55,
    sparse_weight: float = 0.45,
) -> list[SearchResult]:
    """Async retrieval contract for FastAPI and agent nodes."""
    return await asyncio.to_thread(
        hybrid_search, query, top_k, filters, dense_weight, sparse_weight
    )
