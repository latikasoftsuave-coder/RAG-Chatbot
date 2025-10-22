from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from db.database import SessionLocal
from services.chat_service import ChatService
from services.rag_service import RAGService
import asyncio

router = APIRouter()
rag_service = RAGService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, db: Session = Depends(get_db)):
    await websocket.accept()
    chat_service = ChatService(db, rag_service)
    try:
        while True:
            data = await websocket.receive_text()
            if "|" in data:
                session_id, message_content = data.split("|", 1)
            else:
                session_id = client_id
                message_content = data

            chat_service.save_user_message(session_id, message_content)
            history = chat_service.get_last_messages(session_id)

            for chunk in rag_service.stream_answer(message_content, history):
                await websocket.send_text(chunk)
                await asyncio.sleep(0.05)

            chat_service.save_assistant_message(session_id, rag_service.get_answer(message_content, history)["answer"])
    except WebSocketDisconnect:
        print(f"Client disconnected: {client_id}")