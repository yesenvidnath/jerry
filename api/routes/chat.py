"""Chat endpoint invoking the LangGraph assistant."""

import logging

from fastapi import APIRouter, HTTPException

from agent.graph import assistant_graph
from models.api import ActivityEvent, ChatRequest, ChatResponse, Citation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = await assistant_graph.ainvoke({
            "query": request.query,
            "session_id": request.session_id,
            "role": request.role,
            "retry_count": 0,
            "max_retries": 1,
            "activity": [],
            "errors": [],
        })
        return ChatResponse(
            answer=result.get("answer", "I couldn't complete that request."),
            citations=[Citation(**item) for item in result.get("citations", [])],
            activity=[ActivityEvent(**item) for item in result.get("activity", [])],
            error="; ".join(result.get("errors", [])) or None,
        )
    except Exception as exc:
        logger.exception("chat_graph_failed")
        raise HTTPException(status_code=503, detail="The assistant is temporarily unavailable.") from exc
