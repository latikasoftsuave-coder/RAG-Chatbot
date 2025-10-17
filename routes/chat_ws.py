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
            response = chat_service.handle_user_query(session_id, message_content)
            await websocket.send_text(response["answer"])
    except WebSocketDisconnect:
        print(f"Client disconnected: {client_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.send_text(f"❌ Error: {str(e)}")