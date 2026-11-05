# Jerry architecture

```mermaid
flowchart LR
    UI[Streamlit UI] --> API[FastAPI]
    API --> GRAPH[LangGraph assistant]
    GRAPH --> RET[Hybrid retrieval]
    RET --> PC[Pinecone or local demo index]
    GRAPH --> LLM[LLM provider]
    GRAPH --> TOOLS[Analysis and MCP tools]
    GRAPH --> LS[LangSmith tracing]
```

The repository root is the Python package boundary. Feature modules live directly under the root rather than under an `app/` directory. `ui/` hosts Streamlit; `data/sample_docs/` contains demo knowledge; `scripts/` contains repeatable developer commands.
