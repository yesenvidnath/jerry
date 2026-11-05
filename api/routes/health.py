"""Service health endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Return a lightweight liveness response."""
    return {"status": "ok", "service": "jerry"}
