import streamlit as st
import requests
import uuid
import websockets.sync.client as ws_sync
import time

API_URL = "http://127.0.0.1:8000/chat"
WS_URL = "ws://127.0.0.1:8000/chat/ws"
NEW_CHAT_LABEL = "New Chat (Start Fresh)"

st.set_page_config(page_title="RAG Chatbot", page_icon="🤖", layout="wide")
st.title("Chatbot using RAG 🔍")
st.write("Hey, I'm your SS Employee Handbook Guide!")
st.sidebar.title("💬 Chat History")

if "ws_connection" not in st.session_state:
    try:
        st.session_state.ws_connection = ws_sync.connect(f"{WS_URL}/global")
        st.session_state.connection_established = True
    except Exception as e:
        st.error(f"Failed to connect to WebSocket: {e}")
        st.session_state.ws_connection = None
        st.session_state.connection_established = False

def send_message(session_id, message):
    if not st.session_state.get("connection_established"):
        st.error("WebSocket connection not available")
        return None
    formatted_message = f"{session_id}|{message}"
    try:
        st.session_state.ws_connection.send(formatted_message)
        response = st.session_state.ws_connection.recv()
        return response
    except Exception as e:
        try:
            st.session_state.ws_connection = ws_sync.connect(f"{WS_URL}/global")
            st.session_state.connection_established = True
            st.session_state.ws_connection.send(formatted_message)
            response = st.session_state.ws_connection.recv()
            return response
        except Exception as e:
            st.session_state.connection_established = False
            return f"❌ Connection error: {e}"

def load_sessions():
    try:
        sessions_resp = requests.get(f"{API_URL}/sessions/")
        if sessions_resp.status_code == 200:
            all_sessions_data = sessions_resp.json().get("sessions", [])
            all_sessions = []
            session_id_map = {}
            for s in all_sessions_data:
                title = s.get("title") or s.get("id")
                all_sessions.append(title)
                session_id_map[title] = s["id"]
            return all_sessions, session_id_map
    except Exception as e:
        st.error(f"Error loading sessions: {e}")
    return [], {}

all_sessions, session_id_map = load_sessions()

if "selected_session" not in st.session_state:
    st.session_state.selected_session = NEW_CHAT_LABEL
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_loaded_from_db" not in st.session_state:
    st.session_state.session_loaded_from_db = False
if "show_confirm_delete" not in st.session_state:
    st.session_state.show_confirm_delete = False
if "last_session_refresh" not in st.session_state:
    st.session_state.last_session_refresh = time.time()

current_time = time.time()
if current_time - st.session_state.last_session_refresh > 30:
    all_sessions, session_id_map = load_sessions()
    st.session_state.last_session_refresh = current_time

url_session_id = st.query_params.get("session", [None])
if isinstance(url_session_id, list):
    url_session_id = url_session_id[0]
if url_session_id and not st.session_state.session_loaded_from_db:
    for title, sid in session_id_map.items():
        if sid == url_session_id:
            st.session_state.selected_session = title
            st.session_state.session_id = sid
            try:
                history_resp = requests.get(f"{API_URL}/history/{sid}")
                if history_resp.status_code == 200:
                    st.session_state.messages = history_resp.json()
                else:
                    st.session_state.messages = []
            except Exception:
                st.session_state.messages = []
            st.session_state.session_loaded_from_db = True
            break

session_options = [NEW_CHAT_LABEL] + all_sessions

selected_index = session_options.index(
    st.session_state.selected_session) if st.session_state.selected_session in session_options else 0
selected = st.sidebar.selectbox(
    "Select a session",
    session_options,
    index=selected_index,
    key="session_selectbox"
)

if selected != st.session_state.selected_session:
    st.session_state.selected_session = selected
    st.session_state.session_id = session_id_map.get(selected)
    st.query_params["session"] = st.session_state.session_id
    st.session_state.session_loaded_from_db = False

    if selected != NEW_CHAT_LABEL:
        try:
            history_resp = requests.get(f"{API_URL}/history/{st.session_state.session_id}")
            if history_resp.status_code == 200:
                st.session_state.messages = history_resp.json()
            else:
                st.session_state.messages = []
        except Exception:
            st.session_state.messages = []
        st.session_state.session_loaded_from_db = True
    else:
        st.session_state.messages = []
        st.session_state.session_id = None
        st.query_params.clear()
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
                    session_id_to_delete = session_id_map.get(selected, selected)
                    response = requests.delete(f"{API_URL}/delete_session/{session_id_to_delete}")
                    if response.status_code == 200:
                        st.success(f"Session '{selected}' deleted!")
                        st.session_state.selected_session = NEW_CHAT_LABEL
                        st.session_state.session_id = None
                        st.session_state.messages = []
                        st.query_params.clear()
                        st.session_state.show_confirm_delete = False
                        all_sessions, session_id_map = load_sessions()
                        st.rerun()
                    else:
                        st.error("Failed to delete session.")
                except Exception as e:
                    st.error(f"Error: {e}")
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.show_confirm_delete = False
                st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Type your question here..."):
    if selected == NEW_CHAT_LABEL or st.session_state.session_id is None:
        new_id = str(uuid.uuid4())
        st.session_state.session_id = new_id
        st.session_state.messages = []
        st.query_params["session"] = new_id

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        response_placeholder.markdown("▌")

        if st.session_state.session_id:
            response = send_message(st.session_state.session_id, prompt)
            if response:
                response_placeholder.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                error_msg = "❌ Failed to get response from server"
                response_placeholder.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
        else:
            error_msg = "❌ No active session"
            response_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

    all_sessions, session_id_map = load_sessions()
    st.session_state.selected_session = all_sessions[0] if all_sessions else NEW_CHAT_LABEL
    st.rerun()

if hasattr(st, 'scriptrunner') and st.scriptrunner and hasattr(st.scriptrunner, 'on_script_finished'):
    st.scriptrunner.on_script_finished(
        lambda: st.session_state.ws_connection.close() if st.session_state.get('ws_connection') else None
    )