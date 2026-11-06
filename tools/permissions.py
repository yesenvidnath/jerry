"""Central role-to-tool permissions and server-side enforcement."""

from fastapi import HTTPException


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "Viewer": {"chat", "knowledge_search"},
    "Analyst": {"chat", "knowledge_search", "python_analysis", "mcp_tools"},
    "Administrator": {"chat", "knowledge_search", "python_analysis", "mcp_tools", "admin_tools"},
}


class PermissionDenied(PermissionError):
    def __init__(self, role: str, tool: str) -> None:
        super().__init__(f"Role {role} is not permitted to use {tool}.")
        self.role = role
        self.tool = tool


def require_permission(role: str, tool: str) -> None:
    if tool not in ROLE_PERMISSIONS.get(role, set()):
        raise PermissionDenied(role, tool)


def permission_http_error(exc: PermissionDenied) -> HTTPException:
    return HTTPException(status_code=403, detail=str(exc))
