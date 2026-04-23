"""Optimal Routing — Streamlit UI."""

import uuid
import streamlit as st
from app.agent import stream_agent

# --- Page config ---
st.set_page_config(
    page_title="Optimal Routing",
    page_icon="🚢",
    layout="centered",
)

# --- Header ---
st.title("🚢 Optimal Routing")
st.caption("Tell me your port pairs.")

# --- Session state: chat history + thread id ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# --- Render existing chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True)

# --- Chat input ---
if prompt := st.chat_input("e.g. 'New York to Lisbon'"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt, unsafe_allow_html=True)

    with st.chat_message("assistant"):
        with st.spinner("Navigating..."):
            reply = st.write_stream(
                stream_agent(prompt, thread_id=st.session_state.thread_id)
            )
    st.session_state.messages.append({"role": "assistant", "content": reply})