"""Streamlit chat UI with recent history, roles, and activity."""

from uuid import uuid4

import streamlit as st

from core.config import settings
from security.auth import DEFAULT_DEMO_USERS
from ui.api_client import clear_memory, send_chat

st.set_page_config(page_title="Jerry", page_icon="🏦", layout="wide")
st.title("Jerry — Enterprise Knowledge Assistant")
st.caption("Ask about internal policies, incidents, runbooks, and architecture.")

if "session_id" not in st.session_state:
    st.session_state.session_id = uuid4().hex
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_activity" not in st.session_state:
    st.session_state.last_activity = []

with st.sidebar:
    st.subheader("Demo session")
    api_url = st.text_input("Backend URL", value=settings.api_base_url)
    user_id = st.selectbox("Demo account", list(DEFAULT_DEMO_USERS))
    env_name, fallback_token, role = DEFAULT_DEMO_USERS[user_id]
    token = st.text_input("Demo access token", value=__import__("os").getenv(env_name, fallback_token), type="password")
    st.caption(f"Role: **{role}** · Session: {st.session_state.session_id[:8]}…")
    profile = (user_id, role)
    if st.session_state.get("profile") not in (None, profile):
        st.session_state.session_id = uuid4().hex
        st.session_state.messages = []
        st.session_state.last_activity = []
    st.session_state.profile = profile
    if st.button("Clear conversation memory", use_container_width=True):
        try:
            clear_memory(api_url, st.session_state.session_id, token)
            st.session_state.messages = []
            st.session_state.last_activity = []
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
        with st.spinner("Jerry is searching and preparing an answer…"):
            try:
                response = send_chat(api_url, {
                    "query": prompt,
                    "session_id": st.session_state.session_id,
                }, token)
                answer = response["answer"]
                st.markdown(answer)
                citations = response.get("citations", [])
                if citations:
                    with st.expander("Sources"):
                        for citation in citations:
                            st.markdown(f"- **{citation['title']}** (`{citation['document_id']}`)")
                if response.get("error"):
                    st.warning(response["error"])
                st.session_state.messages.append({"role": "assistant", "content": answer, "citations": citations})
                st.session_state.last_activity = response.get("activity", [])
                st.caption(f"Session memory: {response.get('memory_turns', 0)} recent exchange(s)")
            except Exception as exc:
                st.error(str(exc))

if st.session_state.last_activity:
    with st.expander("Agent activity and memory", expanded=False):
        for event in st.session_state.last_activity:
            st.markdown(f"**{event['node']}** · {event['status']} — {event.get('detail', '')}")
