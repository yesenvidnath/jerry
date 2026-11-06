"""Sparse keyword retrieval using BM25 over indexed chunk text."""

import math
import re
from collections import Counter

from models.retrieval import RetrievalFilters, SearchResult
from retrieval.ingest import load_documents
from retrieval.chunking import chunk_document

TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "and", "are", "about", "can", "could", "do", "does", "for",
    "from", "how", "i", "in", "is", "it", "me", "of", "on", "or", "please",
    "say", "tell", "that", "the", "to", "was", "were", "what", "when", "where",
    "which", "who", "why", "with",
}


def _normalize_token(token: str) -> str:
    """Apply a small English plural normalizer for demo BM25 matching."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def tokens(text: str) -> list[str]:
    return [_normalize_token(token) for token in TOKEN_RE.findall(text.lower())]


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


def sparse_search(
    query: str,
    top_k: int = 5,
    filters: RetrievalFilters | None = None,
) -> list[SearchResult]:
    """Search source documents with BM25; useful even before local vector ingestion."""
    documents = load_documents()
    chunks = [chunk for doc in documents for chunk in chunk_document(doc)]
    corpus = [tokens(chunk.text) for chunk in chunks]
    query_terms = set(tokens(query)) - STOPWORDS
    if not query_terms:
        return []
    average_length = sum(map(len, corpus)) / max(len(corpus), 1)
    doc_freq = Counter(term for terms in corpus for term in set(terms))
    scored: list[tuple[float, object]] = []
    k1, b = 1.5, 0.75
    for chunk, terms in zip(chunks, corpus):
        metadata = chunk.metadata()
        if not _matches(metadata, filters):
            continue
        counts = Counter(terms)
        score = 0.0
        for term in query_terms:
            frequency = counts[term]
            if not frequency:
                continue
            idf = math.log(1 + (len(corpus) - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
            denominator = frequency + k1 * (1 - b + b * len(terms) / max(average_length, 1))
            score += idf * (frequency * (k1 + 1)) / denominator
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    output = []
    for rank, (score, chunk) in enumerate(scored[:top_k], start=1):
        output.append(SearchResult(
            chunk_id=chunk.chunk_id, document_id=chunk.document_id, title=chunk.title,
            passage=chunk.text, department=chunk.department, document_type=chunk.document_type,
            access_level=chunk.access_level, created_date=chunk.created_date,
            sparse_score=score, rank=rank,
        ))
    return output
