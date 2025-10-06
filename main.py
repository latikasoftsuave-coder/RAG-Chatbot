from fastapi import FastAPI
from routes import chat_routes

app = FastAPI(title="RAG Chatbot API")

app.include_router(chat_routes.router, prefix="/chat")