from sqlalchemy.orm import Session
from db.models import ChatMessage
from services.rag_service import RAGService

class ChatService:
    def __init__(self, db: Session, rag_service: RAGService):
        self.db = db
        self.rag_service = rag_service

    def save_user_message(self, session_id: str, content: str):
        msg = ChatMessage(session_id=session_id, role="user", content=content)
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def save_assistant_message(self, session_id: str, content: str):
        msg = ChatMessage(session_id=session_id, role="assistant", content=content)
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get_chat_history(self, session_id: str):
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .all()
        )
        return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]

    def get_answer(self, query: str):
        return self.rag_service.get_answer(query)