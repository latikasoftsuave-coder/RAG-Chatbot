from sqlalchemy.orm import Session
from db.models import ChatMessage
from services.rag_service import RAGService
from services.application_service import ApplicationService
from langchain.schema import HumanMessage

class ChatService:
    def __init__(self, db: Session, rag_service: RAGService):
        self.db = db
        self.rag_service = rag_service
        self.workflow_service = ApplicationService()

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

    def get_last_messages(self, session_id: str, limit: int = 10):
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        messages.reverse()
        return [{"role": m.role, "content": m.content} for m in messages]

    def get_chat_history(self, session_id: str):
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .all()
        )
        return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]

    def process_query(self, session_id: str, query: str, history: list = None):
        workflow_session = self.workflow_service.get_session(session_id)
        if workflow_session:
            state = workflow_session["state"]
            if query.lower() in ["cancel", "exit", "stop"]:
                return {"answer": self.workflow_service.cancel_application(session_id)}
            if state == "AWAITING_CONFIRMATION" and query.lower() in ["yes", "confirm"]:
                return {"answer": self.workflow_service.confirm_application(session_id, self.db)}
            next_field = self.workflow_service.next_missing_field(session_id)
            if next_field:
                if len(query.split()) > 6 or "tell me" in query.lower() or "what" in query.lower():
                    return {
                        "answer": (
                            f"You're currently filling your job application. "
                            f"Please provide your **{next_field}**, or type **'cancel'** to stop the application."
                        )
                    }
                self.workflow_service.update_field(session_id, next_field, query)
                next_field = self.workflow_service.next_missing_field(session_id)
                if next_field:
                    return {"answer": f"Got it! Please provide your {next_field} next."}
                else:
                    workflow_session["state"] = "AWAITING_CONFIRMATION"
                    return {"answer": "All details collected. Please confirm your application (yes/no)."}
        intent = self.check_intent(query)
        if "start" in intent.lower() or query.lower() in ["/apply", "apply for a job", "start application"]:
            answer = self.workflow_service.start_application(session_id)
            return {"answer": answer}
        answer = self.get_answer(query, history).get("answer")
        return {"answer": answer}

    def check_intent(self, query: str):
        prompt = f"""
        User message: {query}
        Decide if user wants to start, edit, or view a job application.
        Reply in JSON format: {{"action": "start"}} or {{"action": "none"}}
        """
        result = self.rag_service.fallback_llm.invoke([HumanMessage(content=prompt)])
        return result.content

    def get_answer(self, query: str, history: list = None):
        return self.rag_service.get_answer(query, history)