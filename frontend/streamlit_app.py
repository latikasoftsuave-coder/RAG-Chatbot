import streamlit as st
import requests
import uuid

API_URL = "http://127.0.0.1:8000/chat"

st.set_page_config(page_title="RAG Chatbot", page_icon="🤖", layout="centered")
st.title("Chatbot using RAG 🔍")
st.write("Hey, I'm your SS Employee Handbook Guide!")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    history_resp = requests.get(f"{API_URL}/history/{st.session_state.session_id}")
    if history_resp.status_code == 200:
        for msg in history_resp.json():
            st.session_state.messages.append(msg)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Type your question here:"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.spinner("Thinking... 🤔"):
        response = requests.post(f"{API_URL}/ask_question/", json={"query": prompt, "session_id": st.session_state.session_id})

    if response.status_code == 200:
        answer = response.json().get("answer")

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)