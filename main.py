from fastapi import FastAPI
from routes import chat_routes
from routes import chat_ws

app = FastAPI(title="RAG Chatbot API")

app.include_router(chat_routes.router, prefix="/chat")
app.include_router(chat_ws.router, prefix="/chat")