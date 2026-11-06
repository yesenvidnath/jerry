# Jerry Application Testing Record

**Run date:** 2026-11-06  
**Git branch:** `testing`  
**Scope:** Local application smoke checks and the ten assignment feature areas.

The direct role endpoint matrix below was re-run against the local API on 2026-11-07.

## Result

All 10 feature-area checks and the Streamlit UI smoke check passed (11 checks total, 0 failed). The currently running local API and UI were also reachable:

| Local service | Check | Result |
| --- | --- | --- |
| FastAPI `http://127.0.0.1:8010/` | Root status | HTTP 200 |
| FastAPI `/health` | Health endpoint | HTTP 200 |
| FastAPI `/docs` | OpenAPI documentation | HTTP 200 |
| Streamlit `http://127.0.0.1:8501/` | Web response | HTTP 200 |

Feature checks used FastAPI `TestClient` and Streamlit `AppTest` with the local sample corpus. `LANGSMITH_TRACING` was disabled for the test process, so requests did not export traces to LangSmith.

## Feature checklist

| # | Feature | Checks performed | Result |
| --- | --- | --- | --- |
| 1 | Project foundation | Root, health and API docs respond; protected tools reject a missing token with 401. | PASS |
| 2 | Document ingestion and data model | Loaded five bundled Markdown documents; produced five chunks with document metadata. | PASS |
| 3 | Hybrid search and retrieval | “What are the policies?” returns `POL-SEC-003` as the top result; department filter limits results to payment documents. | PASS |
| 4 | LangGraph assistant flow | Grounded chat returns a citation and graph activity events. | PASS |
| 5 | Recursive analysis (RLM) | Analyst incident-summary request returns RLM activity and citations; batching stays within four batches of at most three passages. | PASS |
| 6 | Session memory and chat | Follow-up in the same session preserves exchange count; clearing memory succeeds. | PASS |
| 7 | Tools and role-based access | Viewer is denied analysis and admin tools; Analyst can use analysis and the employee directory; Administrator can access index status. | PASS |
| 8 | Security and guardrails | Instruction override is rejected; unsafe retrieved content is flagged; secret output is redacted; invalid citations are removed. | PASS |
| 9 | Rate limiting and graceful errors | Oversized chat request returns 422; over-limit call returns 429 with `Retry-After`. | PASS |
| 10 | LangSmith tracing and activity panel | Streaming response includes activity and final events plus a trace ID. | PASS* |
| UI | Streamlit chat UI | AppTest renders the Jerry title and chat input with no app exception. | PASS |

\* The local trace/activity interface was exercised. LangSmith remote trace delivery was deliberately not exercised during this run.

## Coverage limits

- Retrieval was checked with the bundled local BM25/index path. Pinecone and externally hosted semantic embedding providers were not contacted.
- MCP behavior currently uses the application's local demo tool wrappers; an external MCP server was not contacted.
- LangSmith credentials and network delivery were not tested by sending a trace. With tracing disabled, the SSE activity stream and trace ID path were still checked.
- The demo role selector uses server-validated demo tokens and confirms role-based authorization; it is not a separate production login or identity provider.
- The test corpus contains five sample documents, so retrieval quality on a larger or production corpus is not established here.
- Streamlit's bare-mode `AppTest` emitted its standard missing `ScriptRunContext` warning; the app completed without an exception.

## Repeating the checks

From the repository root, with project dependencies installed:

1. Build or refresh the local sample index:

   ```powershell
   python scripts/ingest_sample_data.py
   ```

2. Run the API and UI in separate terminals:

   ```powershell
   uvicorn api.main:app --reload --host 127.0.0.1 --port 8010
   streamlit run ui/streamlit_app.py --server.port 8501
   ```

3. Open `http://127.0.0.1:8501/`, select a demo role, and ask “What are the policies?” to check the grounded response and its source. Use Analyst to exercise analysis/MCP tools; use Administrator to access the admin-only status tool.

4. Open `http://127.0.0.1:8010/docs` to inspect the API schemas and endpoints. The test record above was produced with local in-process API tests, and is not a replacement for deployment tests against configured Pinecone, embedding, MCP, or LangSmith services.

## Role-based access: live endpoint results

These checks were sent to the running FastAPI service at `http://127.0.0.1:8010` on 2026-11-07 with the local demo tokens. Search used `{"query":"security policy","top_k":1}`. Analysis used one valid synthetic passage. Employee, service, and admin-status calls were GET requests.

| Role | `POST /api/tools/search` | `POST /api/tools/analysis` | `GET /api/tools/employees` | `GET /api/tools/services` | `GET /api/tools/admin/index-status` |
| --- | ---: | ---: | ---: | ---: | ---: |
| Viewer | 200 | 403 | 403 | 403 | 403 |
| Analyst | 200 | 200 | 200 | 200 | 403 |
| Administrator | 200 | 200 | 200 | 200 | 200 |

These are observed HTTP results from the local API. All roles could search; Viewer was denied analysis and restricted tools; Analyst could use analysis and employee/service lookups but was denied admin status; Administrator succeeded on every tested tool endpoint. HTTP 403 is the expected result for a prohibited operation.

For implementation details and the role matrix, see [role-based testing](role-based-testing.md). The PowerShell steps below reproduce these checks using the default demo tokens (replace them if environment variables override the defaults).

```powershell
$base = "http://127.0.0.1:8010"
$roles = @(
    @{ Name = "Viewer"; Token = "viewer-demo-token" },
    @{ Name = "Analyst"; Token = "analyst-demo-token" },
    @{ Name = "Administrator"; Token = "admin-demo-token" }
)
$endpoints = @(
    @{ Method = "POST"; Path = "/api/tools/search"; Body = '{"query":"security policy","top_k":1}' },
    @{ Method = "POST"; Path = "/api/tools/analysis"; Body = '{"passages":[{"document_id":"test-doc","title":"Test incident","chunk_id":"test-1","passage":"The incident was caused by a delayed database failover."}]}' },
    @{ Method = "GET"; Path = "/api/tools/employees" },
    @{ Method = "GET"; Path = "/api/tools/services" },
    @{ Method = "GET"; Path = "/api/tools/admin/index-status" }
)
foreach ($role in $roles) {
    foreach ($endpoint in $endpoints) {
        $headers = @{ "X-Demo-Token" = $role.Token }
        try {
            $request = @{ Uri = "$base$($endpoint.Path)"; Method = $endpoint.Method; Headers = $headers; UseBasicParsing = $true }
            if ($endpoint.Body) { $request.ContentType = "application/json"; $request.Body = $endpoint.Body }
            $response = Invoke-WebRequest @request
            $status = [int]$response.StatusCode
        } catch {
            $status = [int]$_.Exception.Response.StatusCode
        }
        "{0,-15} {1,-4} {2,-38} {3}" -f $role.Name, $endpoint.Method, $endpoint.Path, $status
    }
}
```

The role selector in Streamlit only selects a demo identity. To test authorization fully, use each account against the protected endpoints as shown above; this is demo-token authentication, not a production login system.
