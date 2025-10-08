from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from services.pdf_service import PDFService
from services.rag_service import RAGService
from services.chat_service import ChatService
from db.database import SessionLocal, Base, engine

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
        history = chat_service.get_last_messages(request.session_id, limit=10)
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