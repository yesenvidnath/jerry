# Tools and role-based access

FastAPI resolves `X-Demo-Token` to a server-side demo identity in `security/auth.py`; the request body cannot choose its role. Local defaults are provided in `.env.example` for the three demo roles. Change tokens before exposing the demo beyond localhost. This is a demonstration credential scheme, not production authentication.

`tools/permissions.py` is the central permission map. Tool wrappers check authorization immediately before the operation: knowledge search, bounded Python analysis, dummy MCP-style employee/service lookups, and administrator-only index status. The chat graph also blocks analysis intent for Viewers before entering the RLM path; the analysis function independently checks its permission, so a model or graph route cannot bypass the tool boundary.

| Role | Chat and search | Python analysis | MCP-style tools | Admin tools |
|---|---:|---:|---:|---:|
| Viewer | Yes | No | No | No |
| Analyst | Yes | Yes | Yes | No |
| Administrator | Yes | Yes | Yes | Yes |

Protected endpoints are documented at `/docs`: `POST /api/tools/search`, `POST /api/tools/analysis`, `GET /api/tools/employees`, `GET /api/tools/services`, and `GET /api/tools/admin/index-status`. MCP data is local fictional demo content behind an MCP-client-style boundary; it does not require a running MCP server.
