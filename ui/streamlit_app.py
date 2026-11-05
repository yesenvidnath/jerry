"""Streamlit chat UI with live graph events and LangSmith trace metadata."""

import os
from uuid import uuid4

import streamlit as st

from core.config import settings
from security.auth import DEFAULT_DEMO_USERS
from ui.api_client import clear_memory, stream_chat

st.set_page_config(page_title="Jerry", page_icon="🏦", layout="wide")
st.title("Jerry — Enterprise Knowledge Assistant")
st.caption("Ask about internal policies, incidents, runbooks, and architecture.")

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid4().hex
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_activity" not in st.session_state:
    st.session_state.last_activity = []
if "last_trace" not in st.session_state:
    st.session_state.last_trace = None

with st.sidebar:
    st.subheader("Demo session")
    api_url = st.text_input("Backend URL", value=settings.api_base_url)
    user_id = st.selectbox("Demo account", list(DEFAULT_DEMO_USERS))
    env_name, fallback_token, role = DEFAULT_DEMO_USERS[user_id]
    token = st.text_input("Demo access token", value=os.getenv(env_name, fallback_token), type="password")
    st.caption(f"Role: **{role}** · Session: {st.session_state.session_id[:8]}…")
    profile = (user_id, role)
    if st.session_state.get("profile") not in (None, profile):
        st.session_state.session_id = uuid4().hex
        st.session_state.messages = []
        st.session_state.last_activity = []
        st.session_state.last_trace = None
    st.session_state.profile = profile
    if st.button("Clear conversation memory", use_container_width=True):
        try:
            clear_memory(api_url, st.session_state.session_id, token)
            st.session_state.messages = []
            st.session_state.last_activity = []
            st.session_state.last_trace = None
            st.session_state.session_id = uuid4().hex
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("citations"):
            with st.expander("Sources"):
                for citation in message["citations"]:
                    st.markdown(f"- **{citation['title']}** (`{citation['document_id']}`)")

prompt = st.chat_input("Ask Jerry a question…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        activity_box = st.status("Jerry is working…", expanded=True)
        answer_placeholder = st.empty()
        seen_events = []
        final_response = None
        try:
            for message in stream_chat(api_url, {
                "query": prompt,
                "session_id": st.session_state.session_id,
            }, token):
                if message.get("type") == "activity":
                    event = message["event"]
                    seen_events.append(event)
                    activity_box.write(f"**{event['node']}** · {event['status']} — {event.get('detail', '')}")
                elif message.get("type") == "final":
                    final_response = message["response"]
                elif message.get("type") == "error":
                    raise RuntimeError(f"{message.get('detail', 'Request failed')} (trace {message.get('trace_id', 'unavailable')})")

            if final_response is None:
                raise RuntimeError("The backend stream ended before returning an answer.")
            answer = final_response["answer"]
            answer_placeholder.markdown(answer)
            citations = final_response.get("citations", [])
            if citations:
                with st.expander("Sources"):
                    for citation in citations:
                        st.markdown(f"- **{citation['title']}** (`{citation['document_id']}`)")
            if final_response.get("error"):
                st.warning(final_response["error"])
            activity_box.update(label="Assistant run complete", state="complete", expanded=False)
            st.session_state.messages.append({"role": "assistant", "content": answer, "citations": citations})
            st.session_state.last_activity = final_response.get("activity", seen_events)
            st.session_state.last_trace = {
                "trace_id": final_response.get("trace_id"),
                "tracing_enabled": final_response.get("tracing_enabled", False),
                "trace_project": final_response.get("trace_project"),
            }
            st.caption(f"Session memory: {final_response.get('memory_turns', 0)} recent exchange(s)")
        except Exception as exc:
            activity_box.update(label="Assistant run failed", state="error", expanded=True)
            answer_placeholder.error(str(exc))
            st.session_state.last_activity = seen_events

if st.session_state.last_activity:
    with st.expander("Agent activity and observability", expanded=False):
        for event in st.session_state.last_activity:
            stamp = f" · {event['timestamp']}" if event.get("timestamp") else ""
            st.markdown(f"**{event['node']}** · {event['status']}{stamp} — {event.get('detail', '')}")
        if st.session_state.last_trace:
            trace = st.session_state.last_trace
            status = "enabled" if trace["tracing_enabled"] else "disabled (configure LANGSMITH_API_KEY and LANGSMITH_TRACING=true)"
            st.caption(f"LangSmith tracing: {status} · Project: {trace['trace_project'] or 'not configured'} · Trace ID: `{trace['trace_id'] or 'unavailable'}`")
