"""Knowledge search tool with authorization enforced before retrieval."""

from models.retrieval import RetrievalFilters
from retrieval.hybrid import aretrieve
from tools.permissions import require_permission


async def search_knowledge(query: str, role: str, top_k: int = 5, filters: RetrievalFilters | None = None):
    require_permission(role, "knowledge_search")
    return await aretrieve(query, top_k=top_k, filters=filters or RetrievalFilters())
