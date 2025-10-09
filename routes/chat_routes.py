from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.pdf_service import PDFService
from services.rag_service import RAGService
from services.chat_service import ChatService
from db.database import SessionLocal, Base, engine
from db.models import ChatMessage
from sqlalchemy import desc, func

class QuestionRequest(BaseModel):
    query: str
    session_id: str

Base.metadata.create_all(bind=engine)

router = APIRouter()

rag_service = RAGService()
pdf_service = PDFService(rag_service)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        result = await pdf_service.process_pdf_file(file)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask_question/")
async def ask_question(request: QuestionRequest, db: Session = Depends(get_db)):
    try:
        chat_service = ChatService(db, rag_service)
        chat_service.save_user_message(request.session_id, request.query)
        history = chat_service.get_last_messages(request.session_id, limit=None)
        response = chat_service.process_query(request.session_id, request.query, history=history)
        chat_service.save_assistant_message(request.session_id, response["answer"])
        print(request.session_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{session_id}")
async def get_history(session_id: str, db: Session = Depends(get_db)):
    try:
        chat_service = ChatService(db, rag_service)
        return chat_service.get_chat_history(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/")
async def get_sessions(db: Session = Depends(get_db)):
    try:
        sessions = (
            db.query(ChatMessage.session_id)
            .group_by(ChatMessage.session_id)
            .order_by(desc(func.max(ChatMessage.created_at)))
            .all()
        )
        session_list = [s[0] for s in sessions]
        return {"sessions": session_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete_session/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    try:
        messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).all()
        if not messages:
            raise HTTPException(status_code=404, detail="Session not found")
        for msg in messages:
            db.delete(msg)
        db.commit()
        return {"detail": f"Session {session_id} deleted successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))