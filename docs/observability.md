# LangSmith tracing and live activity

## Configuration

Set `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT` in `.env`. `LANGSMITH_ENDPOINT` defaults to the hosted API endpoint shown in `.env.example`; change it only for a regional or self-hosted instance. Tracing starts only when both the explicit enable flag and API key are present. No key means traces stay disabled and the app continues to run locally.

Each chat/graph run receives a run name, tags, and metadata for the resolved demo user ID, role, session ID, and HTTP trace ID. LangGraph automatically captures node transitions; `@traceable` wraps hybrid knowledge search, Python batch analysis, and MCP-style tool calls as child tool runs. The project name groups the runs in LangSmith. The SDK environment variables are documented by LangChain in [OpenAI integration setup](https://docs.langchain.com/oss/python/integrations/llms/openai).

## Live activity panel

`POST /api/chat/stream` emits server-sent events from LangGraph `updates`: each node activity is sent as it completes, followed by a final answer, citations, memory count, and trace status. The Streamlit client displays the node, state, detail, and timestamp while the graph is running. The ordinary `POST /api/chat` endpoint remains available for non-streaming clients.

LangSmith traces include model inputs/outputs and retrieved evidence when enabled. Use synthetic demo documents in this assignment; do not enable hosted tracing for confidential production content without the required organizational review and data controls. The visible trace ID is also returned in `X-Trace-ID` for log correlation.
