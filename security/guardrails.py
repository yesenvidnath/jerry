"""Prompt-injection and response-safety guardrails."""

import re
from typing import Any

INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("instruction_override", re.compile(r"\b(ignore|disregard|override)\b.{0,60}\b(previous|prior|system|developer|all)\b.{0,30}\b(instructions?|rules?|prompt)\b", re.I)),
    ("secret_exfiltration", re.compile(r"\b(reveal|print|dump|exfiltrate|send|expose)\b.{0,50}\b(secret|credential|password|api[ _-]?key|system prompt|private key)\b", re.I)),
    ("unauthorized_tool_use", re.compile(r"\b(bypass|disable|evade)\b.{0,50}\b(permission|authorization|role|safety|guardrail)\b", re.I)),
    ("command_execution", re.compile(r"\b(run|execute)\b.{0,40}\b(shell command|powershell|terminal command|arbitrary code)\b", re.I)),
)

SECRET_OUTPUT_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?i)\b(api[_ -]?key|password|secret|access[_ -]?token)\s*[:=]\s*\S+"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


def inspect_untrusted_text(text: str) -> list[str]:
    return [name for name, pattern in INJECTION_PATTERNS if pattern.search(text)]


def inspect_user_request(text: str) -> list[str]:
    return inspect_untrusted_text(text)


def reject_unsafe_request(text: str) -> str | None:
    flags = inspect_user_request(text)
    if not flags:
        return None
    return "I can’t help with requests to override assistant instructions, expose secrets, bypass access controls, or execute arbitrary commands."


def redact_unsafe_output(text: str, max_length: int = 6000) -> tuple[str, bool]:
    result = text[:max_length]
    redacted = len(text) > max_length
    for pattern in SECRET_OUTPUT_PATTERNS:
        result, count = pattern.subn("[REDACTED]", result)
        redacted = redacted or bool(count)
    return result, redacted


def validate_citations(answer: str, retrieved: list[dict[str, Any]]) -> tuple[str, list[str], bool]:
    citation_re = re.compile(r"\[source:([^\]]+)\]")
    allowed = {str(item.get("document_id", "")) for item in retrieved}
    found = citation_re.findall(answer)
    invalid = [source for source in found if source not in allowed]
    if invalid:
        answer = citation_re.sub(lambda match: "" if match.group(1) not in allowed else match.group(0), answer)
        answer = re.sub(r"\s{2,}", " ", answer).strip()
    valid_used = list(dict.fromkeys(source for source in found if source in allowed))
    return answer, valid_used, bool(invalid)
