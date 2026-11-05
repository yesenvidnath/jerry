"""Small synchronous HTTP client used by the Streamlit foundation UI."""

import json
from urllib.error import URLError
from urllib.request import urlopen


def get_health(base_url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        with urlopen(f"{base_url.rstrip('/')}/health", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return response.status == 200, payload.get("status", "unknown")
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        return False, str(exc)

