"""Small synchronous HTTP client used by Streamlit."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from collections.abc import Iterator


def _auth_headers(token: str) -> dict[str, str]:
    return {"X-Demo-Token": token}


def get_health(base_url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        with urlopen(f"{base_url.rstrip('/')}/health", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return response.status == 200, payload.get("status", "unknown")
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        return False, str(exc)


def send_chat(base_url: str, payload: dict, token: str, timeout: float = 90.0) -> dict:
    request = Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={**_auth_headers(token), "Content-Type": "application/json"},
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


def clear_memory(base_url: str, session_id: str, token: str, timeout: float = 5.0) -> None:
    query = urlencode({"session_id": session_id})
    request = Request(
        f"{base_url.rstrip('/')}/api/chat/memory?{query}",
        headers=_auth_headers(token),
        method="DELETE",
    )
    with urlopen(request, timeout=timeout) as response:
        if response.status not in (200, 204):
            raise RuntimeError(f"Memory clear failed with status {response.status}")


def call_tool(base_url: str, path: str, token: str, payload: dict | None = None, timeout: float = 10.0) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url.rstrip('/')}/api/tools/{path.lstrip('/')}",
        data=data,
        headers={**_auth_headers(token), **({"Content-Type": "application/json"} if data is not None else {})},
        method="POST" if data is not None else "GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API returned {exc.code}: {detail}") from exc

def stream_chat(base_url: str, payload: dict, token: str, timeout: float = 120.0) -> Iterator[dict]:
    """Yield activity events and the final response from the SSE chat endpoint."""
    request = Request(
        f"{base_url.rstrip('/')}/api/chat/stream",
        data=json.dumps(payload).encode("utf-8"),
        headers={**_auth_headers(token), "Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if line.startswith("data: "):
                    yield json.loads(line[6:])
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API returned {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError(f"Could not complete the Jerry request: {exc}") from exc
