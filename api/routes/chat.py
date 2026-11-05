"""Chat endpoint invoking LangGraph with bounded per-session memory."""

import logging

from fastapi import APIRouter, HTTPException, Query

from agent.graph import assistant_graph
from agent.memory import SessionIdentityMismatch, session_memory
from models.api import ActivityEvent, ChatRequest, ChatResponse, Citation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        history = session_memory.get_context(request.session_id, request.user_id, request.role)
        result = await assistant_graph.ainvoke({
            "query": request.query,
            "session_id": request.session_id,
            "user_id": request.user_id,
            "role": request.role,
            "recent_history": history,
            "retry_count": 0,
            "max_retries": 1,
            "activity": [],
            "errors": [],
        })
        answer = result.get("answer", "I couldn't complete that request.")
        turn_count = session_memory.append_exchange(
            request.session_id, request.user_id, request.role, request.query, answer
        )
        activity = list(result.get("activity", []))
        activity.append({
            "node": "memory_update", "status": "complete",
            "detail": f"Saved this exchange; retaining up to 3 recent exchanges ({turn_count} stored)",
        })
        return ChatResponse(
            answer=answer,
            citations=[Citation(**item) for item in result.get("citations", [])],
            activity=[ActivityEvent(**item) for item in activity],
            error="; ".join(result.get("errors", [])) or None,
            memory_turns=turn_count,
        )
    except SessionIdentityMismatch as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("chat_graph_failed")
        raise HTTPException(status_code=503, detail="The assistant is temporarily unavailable.") from exc


@router.delete("/chat/memory", status_code=204)
async def clear_chat_memory(
    session_id: str = Query(min_length=1, max_length=120),
    user_id: str = Query(min_length=1, max_length=120),
) -> None:
    session_memory.clear(session_id, user_id)
