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
            response_dict = chat_service.handle_user_query(session_id, message_content)
            answer = response_dict.get("answer", "")

            chunk_size = 50
            for i in range(0, len(answer), chunk_size):
                await websocket.send_text(answer[i:i+chunk_size])
                await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        print(f"Client disconnected: {client_id}")