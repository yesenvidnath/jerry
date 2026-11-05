"""Validation helpers for user requests, tool arguments, and retrieved passages."""

import re
from typing import Any

DOCUMENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


class UnsafeInput(ValueError):
    pass


class UnsafeRetrievedContent(ValueError):
    pass


def validate_user_query(query: str) -> str:
    normalized = query.strip()
    if not normalized:
        raise UnsafeInput("Question must not be empty.")
    if len(normalized) > 4000:
        raise UnsafeInput("Question exceeds the 4,000 character limit.")
    if CONTROL_RE.search(normalized):
        raise UnsafeInput("Question contains unsupported control characters.")
    return normalized


def validate_tool_text(value: str, name: str, max_length: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise UnsafeInput(f"{name} must not be empty.")
    if len(normalized) > max_length:
        raise UnsafeInput(f"{name} exceeds the {max_length} character limit.")
    if CONTROL_RE.search(normalized):
        raise UnsafeInput(f"{name} contains unsupported control characters.")
    return normalized


def validate_retrieved_passages(passages: list[dict[str, Any]], max_passages: int = 24) -> tuple[list[dict[str, Any]], list[str]]:
    from security.guardrails import inspect_untrusted_text

    if len(passages) > max_passages:
        raise UnsafeRetrievedContent(f"Retrieval returned more than {max_passages} passages.")
    accepted: list[dict[str, Any]] = []
    rejected: list[str] = []
    for item in passages:
        document_id = str(item.get("document_id", ""))
        passage = str(item.get("passage", "")).strip()
        if not DOCUMENT_ID_RE.fullmatch(document_id):
            rejected.append("invalid document identifier")
            continue
        if not passage or len(passage) > 6000 or CONTROL_RE.search(passage):
            rejected.append(f"invalid content in {document_id}")
            continue
        flags = inspect_untrusted_text(passage)
        if flags:
            rejected.append(f"untrusted instruction pattern in {document_id}")
            continue
        clean = dict(item)
        clean["passage"] = passage
        accepted.append(clean)
    return accepted, rejected
