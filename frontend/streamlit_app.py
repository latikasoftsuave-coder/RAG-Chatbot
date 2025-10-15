import streamlit as st
import requests
import asyncio
import uuid
import websockets.sync.client as ws_sync

API_URL = "http://127.0.0.1:8000/chat"
WS_URL = "ws://127.0.0.1:8000/chat/ws"
NEW_CHAT_LABEL = "New Chat (Start Fresh)"

st.set_page_config(page_title="RAG Chatbot", page_icon="🤖", layout="wide")
st.title("Chatbot using RAG 🔍")
st.write("Hey, I'm your SS Employee Handbook Guide!")
st.sidebar.title("💬 Chat History")

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

if "ws_connection" not in st.session_state:
    st.session_state.ws_connection = None

def get_ws(session_id):
    ws = st.session_state.ws_connection
    if ws is None:
        if not session_id:
            raise ValueError("Session ID cannot be None for WebSocket")
        ws = ws_sync.connect(f"{WS_URL}/{session_id}")
        st.session_state.ws_connection = ws
    return ws

def send_receive(session_id, message):
    ws = get_ws(st.session_state.session_id)
    try:
        ws.send(message)
        response = ws.recv()
    except ws_sync.ConnectionClosed:
        ws = ws_sync.connect(f"{WS_URL}/{session_id}")
        st.session_state.ws_connection = ws
        ws.send(message)
        response = ws.recv()
    return response

async def close_ws():
    ws = st.session_state.get("ws_connection")
    if ws:
        await ws.close()
        st.session_state.ws_connection = None

try:
    sessions_resp = requests.get(f"{API_URL}/sessions/")
    all_sessions_data = sessions_resp.json().get("sessions", []) if sessions_resp.status_code == 200 else []
    all_sessions = []
    session_id_map = {}
    for s in all_sessions_data:
        title = s.get("title") or s.get("id")
        all_sessions.append(title)
        session_id_map[title] = s["id"]
except Exception:
    all_sessions = []
    session_id_map = {}

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
                st.session_state.messages = history_resp.json() if history_resp.status_code == 200 else []
            except Exception:
                st.session_state.messages = []
            st.session_state.session_loaded_from_db = True
            break

session_options = [NEW_CHAT_LABEL] + all_sessions
if st.session_state.selected_session not in session_options and st.session_state.selected_session != NEW_CHAT_LABEL:
    session_options.insert(1, st.session_state.selected_session)

selected_index = session_options.index(st.session_state.selected_session) if st.session_state.selected_session in session_options else 0
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
            st.session_state.messages = history_resp.json() if history_resp.status_code == 200 else []
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
    if st.session_state.session_id is None or st.session_state.selected_session == NEW_CHAT_LABEL:
        new_id = str(uuid.uuid4())
        st.session_state.session_id = new_id
        st.session_state.selected_session = "Untitled"
        st.query_params["session"] = new_id
        st.session_state.messages = []

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        ws = get_ws(st.session_state.session_id)
        ws.send(prompt)
        response = ws.recv()
        st.session_state.messages.append({"role": "assistant", "content": response})
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"❌ Something went wrong: {e}"})

    st.rerun()