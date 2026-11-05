"""Small synchronous HTTP client used by Streamlit."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def get_health(base_url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        with urlopen(f"{base_url.rstrip('/')}/health", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return response.status == 200, payload.get("status", "unknown")
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        return False, str(exc)


def send_chat(base_url: str, payload: dict, timeout: float = 90.0) -> dict:
    request = Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API returned {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Could not reach Jerry API: {exc}") from exc


def clear_memory(base_url: str, session_id: str, user_id: str, timeout: float = 5.0) -> None:
    query = urlencode({"session_id": session_id, "user_id": user_id})
    request = Request(f"{base_url.rstrip('/')}/api/chat/memory?{query}", method="DELETE")
    with urlopen(request, timeout=timeout) as response:
        if response.status not in (200, 204):
            raise RuntimeError(f"Memory clear failed with status {response.status}")
