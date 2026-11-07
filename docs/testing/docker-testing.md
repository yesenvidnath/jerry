# Docker development smoke test

**Run date:** 2026-11-07  
**Environment:** Windows, Docker Desktop Linux containers  
**Scope:** Docker Compose services, local sample ingestion, service discovery, and an authenticated chat request.

## Observed results

| Check | Result |
| --- | --- |
| Docker Engine | Available, version `29.9.2` |
| Docker Compose | Version `5.6.1` |
| API and UI Compose services | Both running; API reported healthy |
| `GET http://127.0.0.1:8010/health` | HTTP 200 |
| `GET http://127.0.0.1:8010/docs` | HTTP 200 |
| `GET http://127.0.0.1:8501/` | HTTP 200 |
| UI container to `http://api:8010/health` | HTTP 200; Compose service discovery works |
| `docker compose run --rm ingest` | Passed; 5 sample documents and 5 chunks indexed locally |
| Authenticated `POST /api/chat` | HTTP 200; response included 1 citation and a trace ID |

**Overall:** 10 Docker development smoke checks passed. The API and UI containers remain running after verification.

## Run the same checks

From the repository root in PowerShell:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build -d
docker compose run --rm ingest
```

Check the UI at `http://localhost:8501/`, API health at `http://localhost:8010/health`, and API docs at `http://localhost:8010/docs`. To stop the stack and remove its containers, run:

```powershell
docker compose down
```

## Scope

- The sample ingestion service explicitly uses local embeddings and local indexing; Pinecone credentials are not required.
- The chat smoke test used the local sample corpus and the Viewer demo token.
- This is a local development smoke test, not a production deployment or security assessment.
