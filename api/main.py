"""FastAPI application, trace handling, and sanitized exception mapping."""

from contextlib import asynccontextmanager
import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.routes.chat import router as chat_router
from api.routes.health import router as health_router
from api.routes.tools import router as tools_router
from core.config import settings
from core.logging import configure_logging, reset_trace_id, set_trace_id

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    logger.info("application_started", extra={"environment": settings.app_env})
    yield
    logger.info("application_stopped")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-ID", "")
    if not trace_id or len(trace_id) > 80 or not trace_id.replace("-", "").replace("_", "").isalnum():
        trace_id = uuid.uuid4().hex
    request.state.trace_id = trace_id
    token = set_trace_id(trace_id)
    try:
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response
    finally:
        reset_trace_id(token)


@app.exception_handler(RequestValidationError)
async def request_validation_error(request: Request, exc: RequestValidationError):
    trace_id = getattr(request.state, "trace_id", "-")
    logger.info("request_validation_failed", extra={"trace_id": trace_id})
    return JSONResponse(status_code=422, content={
        "detail": "Invalid request parameters. Check the documented schema and size limits.",
        "trace_id": trace_id,
    })


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    trace_id = getattr(request.state, "trace_id", "-")
    headers = dict(exc.headers or {})
    headers["X-Trace-ID"] = trace_id
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "trace_id": trace_id}, headers=headers)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", "-")
    logger.exception("unhandled_request_error", extra={"trace_id": trace_id})
    return JSONResponse(status_code=500, content={
        "detail": "An unexpected error occurred. Share the trace ID with the support team.",
        "trace_id": trace_id,
    })


app.include_router(health_router)
app.include_router(chat_router)
app.include_router(tools_router)


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "status": "running", "health": "/health", "api_docs": "/docs"}
