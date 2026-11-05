"""LangSmith tracing configuration for LangGraph and child tool runs."""

import logging
import os

logger = logging.getLogger(__name__)


def configure_tracing() -> bool:
    """Enable LangSmith tracing only when a project key is configured."""
    api_key = os.getenv("LANGSMITH_API_KEY", "").strip()
    explicitly_enabled = os.getenv("LANGSMITH_TRACING", "").strip().lower() in {"1", "true", "yes", "on"}
    enabled = explicitly_enabled and bool(api_key)
    os.environ["LANGSMITH_TRACING"] = "true" if enabled else "false"
    if enabled:
        os.environ.setdefault("LANGSMITH_PROJECT", "jerry-assistant")
        endpoint = os.getenv("LANGSMITH_ENDPOINT", "").strip()
        if endpoint:
            os.environ["LANGSMITH_ENDPOINT"] = endpoint
    return enabled


def graph_run_config(user_id: str, role: str, session_id: str, trace_id: str) -> dict:
    """Return tags and non-secret correlation metadata for one conversation run."""
    configure_tracing()
    return {
        "run_name": "jerry_assistant",
        "tags": ["jerry", "chat", role.lower()],
        "metadata": {
            "user_id": user_id,
            "user_role": role,
            "session_id": session_id,
            "trace_id": trace_id,
            "application": "jerry",
        },
    }
