"""Safe, bounded Python analysis over retrieved document passages."""

import re
from collections import Counter
from typing import Any

CAUSE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("downstream gateway timeouts and retry storms", re.compile(r"timeout|retry storm|retries?", re.I)),
    ("queue or worker capacity constraints", re.compile(r"queue|worker capacity|worker saturation", re.I)),
    ("missing or inconsistent idempotency controls", re.compile(r"idempotenc|duplicate request", re.I)),
    ("partner service instability", re.compile(r"partner|gateway|downstream bank", re.I)),
    ("deployment or configuration change", re.compile(r"deploy|configuration|threshold", re.I)),
)


def make_batches(items: list[dict[str, Any]], batch_size: int = 3, max_batches: int = 4) -> list[list[dict[str, Any]]]:
    if batch_size < 1 or max_batches < 1:
        raise ValueError("batch_size and max_batches must be positive")
    return [items[index:index + batch_size] for index in range(0, min(len(items), batch_size * max_batches), batch_size)]


def analyze_batch(batch_number: int, passages: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract bounded, explainable cause signals from a small passage batch."""
    cause_counts: Counter[str] = Counter()
    findings: list[str] = []
    citations: list[dict[str, str]] = []
    documents: list[str] = []
    seen_citations: set[str] = set()

    for item in passages:
        text = str(item.get("passage", ""))
        doc_id = str(item.get("document_id", ""))
        if doc_id and doc_id not in documents:
            documents.append(doc_id)
        for sentence in re.split(r"(?<=[.!?])\s+", text):
            sentence = sentence.strip()
            if not sentence:
                continue
            matched = [label for label, pattern in CAUSE_PATTERNS if pattern.search(sentence)]
            for label in matched:
                cause_counts[label] += 1
                if sentence not in findings:
                    findings.append(sentence[:360])
            if doc_id and doc_id not in seen_citations and matched:
                seen_citations.add(doc_id)
                citations.append({"document_id": doc_id, "title": str(item.get("title", "")), "chunk_id": str(item.get("chunk_id", ""))})

    return {
        "batch_number": batch_number,
        "documents_examined": documents,
        "key_findings": findings[:8],
        "cause_counts": dict(cause_counts),
        "citations": citations,
        "passage_count": len(passages),
    }


def aggregate_findings(batch_results: list[dict[str, Any]]) -> dict[str, Any]:
    total: Counter[str] = Counter()
    documents: list[str] = []
    findings: list[str] = []
    citations: list[dict[str, str]] = []
    cited_ids: set[str] = set()
    for batch in batch_results:
        total.update(batch.get("cause_counts", {}))
        for doc_id in batch.get("documents_examined", []):
            if doc_id not in documents:
                documents.append(doc_id)
        for finding in batch.get("key_findings", []):
            if finding not in findings:
                findings.append(finding)
        for citation in batch.get("citations", []):
            doc_id = citation.get("document_id", "")
            if doc_id and doc_id not in cited_ids:
                cited_ids.add(doc_id)
                citations.append(citation)
    return {"cause_counts": dict(total), "documents_examined": documents, "key_findings": findings, "citations": citations}
