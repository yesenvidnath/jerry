"""Bounded in-process conversation memory for demo sessions."""

from collections import OrderedDict
from threading import RLock
from typing import Any


class SessionIdentityMismatch(ValueError):
    """Raised if a caller tries to reuse a session as a different user or role."""


class SessionMemoryStore:
    def __init__(self, max_sessions: int = 1000, max_turns: int = 6) -> None:
        self.max_sessions = max_sessions
        self.max_turns = max_turns
        self._sessions: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = RLock()

    @staticmethod
    def _key(session_id: str, user_id: str) -> str:
        return f"{user_id}:{session_id}"

    def get_context(self, session_id: str, user_id: str, role: str) -> list[dict[str, str]]:
        key = self._key(session_id, user_id)
        with self._lock:
            record = self._sessions.get(key)
            if record is None:
                return []
            if record["role"] != role or record["user_id"] != user_id:
                raise SessionIdentityMismatch("This session is bound to a different user or role.")
            self._sessions.move_to_end(key)
            return [dict(turn) for turn in record["turns"][-self.max_turns:]]

    def append_exchange(self, session_id: str, user_id: str, role: str, user_message: str, assistant_message: str) -> int:
        key = self._key(session_id, user_id)
        with self._lock:
            record = self._sessions.get(key)
            if record is None:
                record = {"user_id": user_id, "role": role, "turns": []}
                self._sessions[key] = record
            elif record["role"] != role or record["user_id"] != user_id:
                raise SessionIdentityMismatch("This session is bound to a different user or role.")
            record["turns"].extend([
                {"role": "user", "content": user_message[:4000]},
                {"role": "assistant", "content": assistant_message[:4000]},
            ])
            record["turns"] = record["turns"][-self.max_turns:]
            self._sessions.move_to_end(key)
            while len(self._sessions) > self.max_sessions:
                self._sessions.popitem(last=False)
            return len(record["turns"]) // 2

    def clear(self, session_id: str, user_id: str) -> None:
        with self._lock:
            self._sessions.pop(self._key(session_id, user_id), None)


def contextualize_query(query: str, history: list[dict[str, str]]) -> str:
    """Resolve short follow-ups from recent user turns, never from assistant claims."""
    previous_questions = [turn["content"] for turn in history if turn.get("role") == "user"]
    if not previous_questions:
        return query
    normalized = query.casefold().strip()
    follow_up = len(query.split()) <= 12 or normalized.startswith(("what about", "how about", "and ", "what if", "why did it", "how does it"))
    if not follow_up:
        return query
    previous = previous_questions[-1]
    if previous.casefold().strip() == normalized:
        return query
    return f"Earlier question: {previous}\nFollow-up question: {query}"


def format_recent_history(history: list[dict[str, str]], max_chars: int = 3000) -> str:
    lines = []
    used = 0
    for turn in history[-6:]:
        role = turn.get("role", "user")
        content = turn.get("content", "").strip()
        line = f"{role}: {content}"
        if used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines)


session_memory = SessionMemoryStore(max_sessions=1000, max_turns=6)
