# Session memory and chat

`agent/memory.py` provides a thread-safe, bounded in-process store, retains the latest 3 user/assistant exchanges, and caps the store at 1,000 sessions. Records are keyed by session and user and bound to the role first supplied. A role mismatch returns HTTP 409. `DELETE /api/chat/memory?session_id=…&user_id=…` clears the demo session.

The API passes recent turns to LangGraph. Short follow-up searches combine the latest prior user question with the current question; prior assistant text is never used as retrieval evidence. The optional model prompt receives a capped history window marked as context only. The Streamlit UI keeps the visible transcript in browser session state and exposes a clear-memory action. Backend memory is process-local and resets on restart, an intentional simple POC tradeoff.
