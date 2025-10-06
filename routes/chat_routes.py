from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from services.pdf_service import PDFService
from services.rag_service import RAGService

class QuestionRequest(BaseModel):
    query: str

router = APIRouter()

rag_service = RAGService()
pdf_service = PDFService(rag_service)

@router.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        result = await pdf_service.process_pdf_file(file)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ask_question/")
async def ask_question(request: QuestionRequest):
    try:
        result = rag_service.get_answer(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
