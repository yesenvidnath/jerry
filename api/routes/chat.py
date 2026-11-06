"""Chat endpoints with memory, LangSmith tracing, and streamed activity."""

import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from api.dependencies import enforce_rate_limit
from agent.graph import assistant_graph
from agent.memory import SessionIdentityMismatch, session_memory
from models.api import ActivityEvent, ChatRequest, ChatResponse, Citation
from observability.events import make_activity_event
from observability.tracing import configure_tracing, graph_run_config
from security.auth import DemoUser, get_current_user
from tools.permissions import PermissionDenied, require_permission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"], dependencies=[Depends(enforce_rate_limit)])


def _initial_state(request: ChatRequest, user: DemoUser, history: list[dict[str, str]]) -> dict:
    return {
        "query": request.query, "session_id": request.session_id,
        "user_id": user.user_id, "role": user.role,
        "recent_history": history, "retry_count": 0, "max_retries": 1,
        "activity": [], "errors": [],
    }


def _run_config(request: ChatRequest, user: DemoUser, trace_id: str) -> dict:
    return graph_run_config(user.user_id, user.role, request.session_id, trace_id)


def _finish_result(result: dict, request: ChatRequest, user: DemoUser, history: list[dict[str, str]], trace_id: str) -> ChatResponse:
    answer = result.get("answer", "I couldn't complete that request.")
    rejected = any("Request rejected by security guardrail" in error for error in result.get("errors", []))
    if rejected:
        turn_count = len(history) // 2
    else:
        turn_count = session_memory.append_exchange(request.session_id, user.user_id, user.role, request.query, answer)
    activity = list(result.get("activity", []))
    activity.append(make_activity_event("memory_update", "complete", f"Saved exchange; up to 3 recent exchanges ({turn_count} stored)"))
    tracing_enabled = configure_tracing()
    return ChatResponse(
        answer=answer,
        citations=[Citation(**item) for item in result.get("citations", [])],
        activity=[ActivityEvent(**item) for item in activity],
        error="; ".join(result.get("errors", [])) or None,
        memory_turns=turn_count,
        trace_id=trace_id,
        tracing_enabled=tracing_enabled,
        trace_project=os.getenv("LANGSMITH_PROJECT", "jerry-assistant") if tracing_enabled else None,
    )


async def _history(request: ChatRequest, user: DemoUser) -> list[dict[str, str]]:
    require_permission(user.role, "chat")
    return session_memory.get_context(request.session_id, user.user_id, user.role)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request, user: DemoUser = Depends(get_current_user)) -> ChatResponse:
    trace_id = getattr(http_request.state, "trace_id", "-")
    try:
        history = await _history(request, user)
        result = await assistant_graph.ainvoke(
            _initial_state(request, user, history),
            config=_run_config(request, user, trace_id),
        )
        return _finish_result(result, request, user, history, trace_id)
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SessionIdentityMismatch as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("chat_graph_failed", extra={"trace_id": trace_id})
        raise HTTPException(status_code=503, detail="The assistant is temporarily unavailable.") from exc


@router.post("/chat/stream")
async def stream_chat(request: ChatRequest, http_request: Request, user: DemoUser = Depends(get_current_user)):
    trace_id = getattr(http_request.state, "trace_id", "-")

    async def events():
        try:
            history = await _history(request, user)
            state = _initial_state(request, user, history)
            config = _run_config(request, user, trace_id)
            result: dict = {}
            async for update in assistant_graph.astream(state, config=config, stream_mode="updates"):
                for _node_name, patch in update.items():
                    result.update(patch)
                    activities = patch.get("activity", []) if isinstance(patch, dict) else []
                    if activities:
                        event = activities[-1]
                        yield "data: " + json.dumps({"type": "activity", "event": event}, ensure_ascii=False) + "\n\n"
            response = _finish_result(result, request, user, history, trace_id)
            yield "data: " + json.dumps({"type": "final", "response": response.model_dump(mode="json")}, ensure_ascii=False) + "\n\n"
        except (PermissionDenied, SessionIdentityMismatch) as exc:
            yield "data: " + json.dumps({"type": "error", "detail": str(exc), "trace_id": trace_id}) + "\n\n"
        except Exception:
            logger.exception("streaming_chat_failed", extra={"trace_id": trace_id})
            yield "data: " + json.dumps({"type": "error", "detail": "The assistant is temporarily unavailable.", "trace_id": trace_id}) + "\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Trace-ID": trace_id})


@router.delete("/chat/memory", status_code=204)
async def clear_chat_memory(
    session_id: str = Query(min_length=1, max_length=120),
    user: DemoUser = Depends(get_current_user),
) -> None:
    session_memory.clear(session_id, user.user_id)
