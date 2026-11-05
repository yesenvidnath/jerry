"""FastAPI application and startup configuration."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from api.routes.chat import router as chat_router
from api.routes.health import router as health_router
from core.config import settings
from core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    logging.getLogger(__name__).info("application_started", extra={"environment": settings.app_env})
    yield
    logging.getLogger(__name__).info("application_stopped")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
app.include_router(chat_router)


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    """Give a friendly landing response at the API base URL."""
    return {"service": settings.app_name, "status": "running", "health": "/health", "api_docs": "/docs"}
