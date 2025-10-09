import streamlit as st
import requests
import uuid

API_URL = "http://127.0.0.1:8000/chat"
NEW_CHAT_LABEL = "New Chat (Start Fresh)"

st.set_page_config(page_title="RAG Chatbot", page_icon="🤖", layout="wide")
st.title("Chatbot using RAG 🔍")
st.write("Hey, I'm your SS Employee Handbook Guide!")

st.sidebar.title("💬 Chat History")

try:
    sessions_resp = requests.get(f"{API_URL}/sessions/")
    all_sessions = sessions_resp.json().get("sessions", []) if sessions_resp.status_code == 200 else []
except Exception:
    all_sessions = []

session_list = [NEW_CHAT_LABEL] + all_sessions

params = st.query_params
url_session = params.get("session", [None])[0] if isinstance(params.get("session"), list) else params.get("session")

if "selected_session" not in st.session_state:
    st.session_state.selected_session = url_session or NEW_CHAT_LABEL
if "session_id" not in st.session_state:
    st.session_state.session_id = url_session
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_loaded_from_db" not in st.session_state:
    st.session_state.session_loaded_from_db = False
if "show_confirm_delete" not in st.session_state:
    st.session_state.show_confirm_delete = False

selected = st.sidebar.selectbox(
    "Select a session",
    session_list,
    index=session_list.index(st.session_state.selected_session)
    if st.session_state.selected_session in session_list else 0,
)

if selected != st.session_state.selected_session:
    st.session_state.selected_session = selected
    st.session_state.session_loaded_from_db = False

    if selected != NEW_CHAT_LABEL:
        st.query_params["session"] = selected
        try:
            history_resp = requests.get(f"{API_URL}/history/{selected}")
            st.session_state.messages = history_resp.json() if history_resp.status_code == 200 else []
        except Exception:
            st.session_state.messages = []
        st.session_state.session_id = selected
        st.session_state.session_loaded_from_db = True
    else:
        st.query_params.clear()
        st.session_state.session_id = None
        st.session_state.messages = []
    st.rerun()

if selected != NEW_CHAT_LABEL:
    if st.sidebar.button("🗑️ Delete Session"):
        st.session_state.show_confirm_delete = True

    if st.session_state.show_confirm_delete:
        st.sidebar.warning(f"Are you sure you want to delete session '{selected}'?")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("✅ Yes"):
                try:
                    response = requests.delete(f"{API_URL}/delete_session/{selected}")
                    if response.status_code == 200:
                        st.success(f"Session {selected} deleted!")
                        st.session_state.selected_session = NEW_CHAT_LABEL
                        st.session_state.session_id = None
                        st.session_state.messages = []
                        st.query_params.clear()
                        st.session_state.show_confirm_delete = False
                        st.rerun()
                    else:
                        st.error("Failed to delete session.")
                except Exception as e:
                    st.error(f"Error: {e}")
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.show_confirm_delete = False
                st.rerun()

if (
    st.session_state.session_id
    and not st.session_state.messages
    and st.session_state.session_id != NEW_CHAT_LABEL
):
    try:
        history_resp = requests.get(f"{API_URL}/history/{st.session_state.session_id}")
        st.session_state.messages = history_resp.json() if history_resp.status_code == 200 else []
    except Exception:
        st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Type your question here..."):
    if st.session_state.session_id is None:
        new_id = str(uuid.uuid4())
        st.session_state.session_id = new_id
        st.session_state.selected_session = new_id
        st.query_params["session"] = new_id
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.spinner("Thinking... 🤔"):
        response = requests.post(
            f"{API_URL}/ask_question/",
            json={"query": prompt, "session_id": st.session_state.session_id},
        )
    answer = (
        response.json().get("answer", "❌ No answer returned.")
        if response.status_code == 200
        else "❌ Something went wrong."
    )
    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.markdown(answer)
    if st.session_state.selected_session not in session_list:
        st.rerun()