"""Dummy enterprise MCP-style tool data for the assessment demo.

These Python functions mimic the boundaries an MCP client would call. The
permissions layer runs before data is returned; no external MCP server is needed.
"""

EMPLOYEES = [
    {"employee_id": "E-104", "name": "Maya Perera", "department": "Payments", "title": "Payments Operations Lead"},
    {"employee_id": "E-218", "name": "Ravi Silva", "department": "Technology", "title": "Platform Engineer"},
]

SERVICES = [
    {"service_id": "SVC-PAY", "name": "Payment Authorization API", "owner": "Payments Engineering", "tier": "critical"},
    {"service_id": "SVC-SETTLE", "name": "Settlement Processor", "owner": "Payments Operations", "tier": "critical"},
]


def list_employees(role: str) -> list[dict[str, str]]:
    from tools.permissions import require_permission
    require_permission(role, "mcp_tools")
    return [dict(item) for item in EMPLOYEES]


def list_services(role: str) -> list[dict[str, str]]:
    from tools.permissions import require_permission
    require_permission(role, "mcp_tools")
    return [dict(item) for item in SERVICES]
