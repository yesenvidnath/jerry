# Jerry

Jerry is an enterprise knowledge assistant built in ordered feature stages. This branch implements the **project foundation**: FastAPI health service, Streamlit connectivity page, environment configuration, JSON logs, and sample company documents.

## Requirements

- Python 3.11 or newer
- pip

## Setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

## Run

Start the API in one terminal:

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 8010
```

Open `http://127.0.0.1:8010/health` or the interactive API docs at `http://127.0.0.1:8010/docs`.

Start the UI in another terminal:

```powershell
streamlit run ui/streamlit_app.py
```

Use **Check backend** in the page to call the API health endpoint. Set `API_BASE_URL` in `.env` if the API runs at another address. The app reads `.env` automatically when started with the setup above (via `python-dotenv`/Streamlit environment loading as later stages are added); environment variables can also be set directly in the shell.

## Sample knowledge documents

`data/sample_docs/` contains fictional payments incident reports, an operational runbook, a security policy, and architecture notes for upcoming ingestion and retrieval work. They are synthetic demo content.

## Architecture and roadmap

See [architecture](docs/architecture.md) and [development flow](docs/development-flow.md). API endpoints are asynchronous; structured JSON logs go to stdout. No model, Pinecone, or LangSmith credentials are required for this foundation stage.

