"""Structured JSON logging with request trace context."""

from contextvars import ContextVar
import json
import logging
from datetime import datetime, timezone

trace_id_context: ContextVar[str] = ContextVar("trace_id", default="-")


def set_trace_id(trace_id: str):
    return trace_id_context.set(trace_id)


def reset_trace_id(token) -> None:
    trace_id_context.reset(token)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", trace_id_context.get()),
        }
        for field in ("user_id", "environment", "service"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
