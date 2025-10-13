from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from db.database import SessionLocal
from services.chat_service import ChatService
from services.rag_service import RAGService

router = APIRouter()
rag_service = RAGService()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, db: Session = Depends(get_db)):
    await websocket.accept()
    chat_service = ChatService(db, rag_service)
    try:
        while True:
            data = await websocket.receive_text()
            # data is the user's message
            response = chat_service.handle_user_query(session_id, data)
            # send assistant's response
            await websocket.send_text(response["answer"])
    except WebSocketDisconnect:
        print(f"Client disconnected: {session_id}")