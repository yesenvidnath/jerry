"""Timestamped activity events shared by graph nodes and the UI."""

from datetime import datetime, timezone


def make_activity_event(node: str, status: str, detail: str = "") -> dict[str, str]:
    return {
        "node": node,
        "status": status,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
