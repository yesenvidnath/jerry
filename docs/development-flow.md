# Development flow

Implement and integrate features into `features` in this dependency order:

1. Project foundation
2. Document ingestion and data model
3. Hybrid search and retrieval
4. LangGraph assistant flow
5. Recursive analysis (RLM)
6. Session memory and chat
7. Tools and role based access
8. Security and guardrails
9. Rate limiting and graceful errors
10. LangSmith tracing and activity panel
11. Demo readiness and documentation

Create a feature branch for each stage; merge into `features` when its acceptance points work. Promote stable demos through `production` and merge the final hand-in into `main`.
