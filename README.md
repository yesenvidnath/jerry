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
