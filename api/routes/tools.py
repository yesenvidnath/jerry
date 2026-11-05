"""Protected tool endpoints for search, analysis, and dummy MCP data."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from models.retrieval import RetrievalFilters
from models.tools import AnalysisToolRequest, SearchToolRequest
from security.auth import DemoUser, get_current_user
from tools.analysis import analyze_batch
from tools.knowledge_search import search_knowledge
from tools.mcp_client import list_employees, list_services
from tools.permissions import PermissionDenied, require_permission

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.post("/search")
async def search(request: SearchToolRequest, user: DemoUser = Depends(get_current_user)):
    try:
        results = await search_knowledge(
            request.query, user.role, request.top_k,
            RetrievalFilters(department=request.department, document_type=request.document_type),
        )
        return {"results": [result.model_dump(mode="json") for result in results]}
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/analysis")
async def analyze(request: AnalysisToolRequest, user: DemoUser = Depends(get_current_user)):
    try:
        result = await run_in_threadpool(
            analyze_batch, 1, [item.model_dump() for item in request.passages], user.role
        )
        return result
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/employees")
async def employees(user: DemoUser = Depends(get_current_user)):
    try:
        return {"employees": list_employees(user.role)}
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/services")
async def services(user: DemoUser = Depends(get_current_user)):
    try:
        return {"services": list_services(user.role)}
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/admin/index-status")
async def index_status(user: DemoUser = Depends(get_current_user)):
    try:
        require_permission(user.role, "admin_tools")
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    index_path = Path(__file__).resolve().parents[2] / "data" / "local_index.jsonl"
    return {"local_index_exists": index_path.exists(), "local_index_path": str(index_path)}
