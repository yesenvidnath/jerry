"""Knowledge search tool with authorization and timeout/error boundaries."""

import asyncio

from core.config import settings
from core.errors import DownstreamServiceError
from models.retrieval import RetrievalFilters
from retrieval.hybrid import aretrieve
from tools.permissions import require_permission


async def search_knowledge(query: str, role: str, top_k: int = 5, filters: RetrievalFilters | None = None):
    require_permission(role, "knowledge_search")
    try:
        return await asyncio.wait_for(
            aretrieve(query, top_k=top_k, filters=filters or RetrievalFilters()),
            timeout=settings.retrieval_timeout_seconds,
        )
    except TimeoutError as exc:
        raise DownstreamServiceError("retrieval", "Knowledge search timed out. Please retry.") from exc
    except Exception as exc:
        raise DownstreamServiceError("retrieval", "Knowledge search is temporarily unavailable.") from exc
