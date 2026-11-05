"""Minimal Streamlit page that verifies connectivity to the API."""

import streamlit as st

from core.config import settings
from ui.api_client import get_health

st.set_page_config(page_title="Jerry", page_icon="🏦")
st.title("Jerry — Enterprise Knowledge Assistant")
st.caption("Project foundation · API connectivity check")

api_url = st.text_input("Backend URL", value=settings.api_base_url)
if st.button("Check backend", type="primary"):
    with st.spinner("Checking health endpoint..."):
        healthy, detail = get_health(api_url)
    if healthy:
        st.success(f"Backend is reachable: {detail}")
    else:
        st.error(f"Backend is not reachable: {detail}")

st.info("Chat, retrieval, and agent features will be added in the next development stages.")
