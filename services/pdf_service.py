import os
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from services.rag_service import RAGService

os.makedirs("pdfs", exist_ok=True)

class PDFService:
    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service

    async def process_pdf_file(self, file):
        file_path = f"pdfs/{file.filename}"
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        text = self.read_pdf(file_path)
        chunks = self.split_text(text)
        self.rag_service.create_vectorstore(chunks)
        return {"message": "PDF processed and vectorstore created."}

    def read_pdf(self, file_path: str):
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    def split_text(self, text: str, chunk_size=500, chunk_overlap=50):
        splitter = CharacterTextSplitter(
            separator="\n",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        return splitter.split_text(text)
