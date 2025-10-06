import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/chat"

st.set_page_config(page_title="RAG Chatbot", page_icon="🤖", layout="centered")
st.title("Chatbot using RAG 🔍")
st.write("Hey, I'm your SS Employee Handbook Guide!")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
if prompt := st.chat_input("Type your question here:"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call backend
    with st.spinner("Thinking... 🤔"):
        response = requests.post(f"{API_URL}/ask_question/", json={"query": prompt})

    if response.status_code == 200:
        answer = response.json().get("answer")
    else:
        answer = "❌ Something went wrong while fetching the answer."

    # Add bot message
    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)
