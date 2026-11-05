# Rate limiting and resilience

Authenticated chat and tool routes use a per-user token bucket. `RATE_LIMIT_CAPACITY` sets burst capacity and `RATE_LIMIT_REFILL_PER_MINUTE` sets the steady refill. Defaults are 20 requests in a burst and 10 tokens per minute. A rejected request returns HTTP 429 with a `Retry-After` header; `/health` and `/` remain available.

Retrieval, LLM, and tool timeouts are configurable with `RETRIEVAL_TIMEOUT_SECONDS`, `LLM_TIMEOUT_SECONDS`, and `TOOL_TIMEOUT_SECONDS`. Pinecone/retrieval failures produce a safe answer/error, OpenAI failures fall back to cited extractive output, MCP-style calls have bounded timeouts and safe responses, and invalid requests receive a sanitized 422. Unexpected API errors return a generic message and trace ID; the detailed exception is written to structured logs. Responses include an `X-Trace-ID` header, and JSON logs carry that ID for support correlation.

The token bucket is process-local. For multiple API workers or hosts, use a shared store such as Redis so limits apply across the deployment.
