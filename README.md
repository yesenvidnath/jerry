# Jerry

Jerry is an enterprise knowledge assistant built in ordered feature stages. This branch implements **document ingestion and data modeling** on top of the project foundation.

## Requirements and setup

- Python 3.11 or newer
- Install dependencies: `python -m pip install -r requirements.txt`
- Copy `.env.example` to `.env` and set credentials only for optional hosted services.

## Run the API and UI

API (port 8010):

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 8010
```

Streamlit (second terminal):

```powershell
streamlit run ui/streamlit_app.py
```

## Ingest the sample documents

The default local mode requires no API keys and writes chunk records and reproducible local feature-hash vectors to `data/local_index.jsonl`:

```powershell
python scripts/ingest_sample_data.py
```

To send vectors to Pinecone, configure `PINECONE_API_KEY`, `PINECONE_INDEX`, and `PINECONE_NAMESPACE`, choose an embedding provider compatible with the index dimension, then run:

```powershell
python scripts/ingest_sample_data.py --backend pinecone
```

The default local hash embeddings are a dependency-free demonstration vectorizer, **not semantic embeddings**. For production-style vectors, set `EMBEDDING_PROVIDER=openai`, provide `OPENAI_API_KEY`, and install the optional OpenAI SDK listed in `requirements.txt`. Create a Pinecone index whose dimension matches the selected embedding model before ingestion. Pinecone integration is optional and is not considered configured until these steps succeed.

Chunk metadata preserves document ID, title, chunk index, department, document type, access level, and creation date for citation and future retrieval filters. Sample documents are fictional.

VECTOR_BACKEND=local

## Chat assistant (stage 4)

The FastAPI chat endpoint is `POST http://127.0.0.1:8010/api/chat`. A minimal request body is:

```json
{"query":"What caused the settlement delay?","session_id":"demo","role":"Viewer"}
```

The LangGraph workflow validates the request, classifies intent, retrieves evidence, checks support, performs at most one wider retrieval retry, generates a grounded answer, and validates citations against retrieved document IDs. The API returns the answer, citations, activity events, and a safe error summary. You can try it at `http://127.0.0.1:8010/docs`.

By default `LLM_PROVIDER=local` returns cited excerpts from the retrieved material without requiring an LLM key. Set `LLM_PROVIDER=openai` and `OPENAI_API_KEY` to use the configured chat model. If that provider fails, the graph records the failure and falls back to extractive cited output. The local answer is intentionally extractive; it is not presented as a model-generated synthesis.

## Recursive analysis (RLM-style)

Analysis-shaped questions such as “Summarize payment failure incidents from last year and identify recurring root causes” route into a separate LangGraph path. The path builds an explicit Python analysis plan, searches only incident reports with relevant metadata filters, splits the retrieved passages into batches of at most 3, processes no more than 4 batches, and aggregates cause signals with supporting source IDs. The activity list shows planning, search, each batch, and aggregation. “Last year” means the previous calendar year; “past year” means the trailing 365 days.

This is a bounded RLM demonstration: targeted retrieval and Python-controlled subtask/batch analysis avoid loading the whole corpus into an LLM prompt. Cause categories use transparent Python phrase patterns rather than an LLM judgment, and the answer states that limitation. Current sample reports are dated in 2025; if asked for the past 365 days in 2026, a no-results answer is expected. The previous calendar year 2025 query will match the included samples.

## Session memory and chat

Chat now runs through the Streamlit interface and `POST /api/chat`. Each UI session gets a unique session ID and carries the demo user ID and selected role to the backend. The API stores up to the 3 most recent exchanges per session in bounded process memory (up to 1,000 sessions). Recent user questions can clarify short follow-ups; previous assistant text is context only and retrieved documents remain the source of facts. OpenAI prompts receive a small conversation window with that same rule. Use **Clear conversation memory** to start a fresh session.

This demo memory is in-process and is cleared when the API restarts; it is not durable across deployments or shared across multiple workers. The API binds a session to the first user ID and role that uses it and rejects a change for that session. The current role/user fields are demo inputs, not authenticated identity; the RBAC stage will replace them with server-verified identity.

## Tools and role-based access

Use the demo account selector in the Streamlit sidebar. The backend derives the role from the `X-Demo-Token` header; the chat body no longer accepts a role. Local example tokens live in `.env.example` and can be overridden with environment variables. Do not deploy the example tokens as real credentials.

```bash
curl -X POST http://127.0.0.1:8010/api/chat \
  -H "X-Demo-Token: viewer-demo-token" \
  -H "Content-Type: application/json" \
  -d '{"query":"What caused settlement delays?","session_id":"demo-session"}'
```

Viewers can chat and search. Analysts can also run structured Python analysis and MCP-style employee/service tools. Administrators can use all tools, including `GET /api/tools/admin/index-status`. A Viewer request routed to multi-document analysis is safely denied with a visible authorization event; direct calls to protected analyst tools return HTTP 403. See [role permissions and endpoints](docs/rbac-tools.md).
