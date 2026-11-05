# LangGraph assistant flow

The graph carries explicit query, role, session ID, selected route, retrieved passages, answer, citations, activity, errors, and retry count in `models/state.py`. `agent/graph.py` builds the workflow; `agent/nodes.py` holds validation, retrieval, evidence assessment, response, and citation checks. The supervisor currently distinguishes knowledge lookup from analysis-shaped intent, while both use the stage 3 retriever. Stage 5 will add bounded batch analysis.

A no-evidence answer is explicit. One wider retrieval retry is allowed, preventing an unbounded loop. The local response mode is extractive. Optional OpenAI generation receives only retrieved evidence and is instructed to treat its text as untrusted data. Citation IDs are checked against retrieved document IDs before returning.
