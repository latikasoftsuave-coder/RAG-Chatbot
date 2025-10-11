from sqlalchemy.orm import Session
from db.models import ChatMessage
from services.rag_service import RAGService
from services.application_service import ApplicationService
from langchain.schema import HumanMessage
import json

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

    def save_user_message(self, session_id: str, content: str):
        first_msg = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .first()
        )
        title = None
        if not first_msg:
            title = self.generate_session_title_from_content(content)

        msg = ChatMessage(session_id=session_id, role="user", content=content, title=title)
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def generate_session_title_from_content(self, content: str):
        prompt = f"Generate a concise 3–5 word title for this chat:\n\n{content}"
        try:
            response = self.rag_service.fallback_llm.invoke([HumanMessage(content=prompt)])
            title = response.content.strip()
            if (title.startswith('"') and title.endswith('"')) or (title.startswith("'") and title.endswith("'")):
                title = title[1:-1].strip()
            return title if title else None
        except Exception:
            return None

    def generate_session_title(self, session_id: str):
        first_msg = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id, ChatMessage.role == "user")
            .order_by(ChatMessage.created_at.asc())
            .first()
        )
        if not first_msg:
            return session_id

        return first_msg.title or first_msg.content[:50]

    def get_chat_history(self, session_id: str):
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .all()
        )
        return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]

    def get_last_messages(self, session_id: str, limit: int = None):
        query = self.db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(
            ChatMessage.created_at.desc())
        if limit:
            query = query.limit(limit)
        messages = query.all()
        return [{"role": m.role, "content": m.content} for m in messages]

    def process_query(self, session_id: str, query: str, history: list = None):
        workflow_session = self.workflow_service.get_session(session_id)
        if "apply" in query.lower() and "job" in query.lower():
            answer = self.workflow_service.start_application(session_id)
            return {"answer": answer}
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
        try:
            intent = json.loads(intent).get("action", "none")
        except:
            intent = "none"
        if "start" in intent or query.lower() in ["/apply", "apply for a job", "start application"]:
            answer = self.workflow_service.start_application(session_id)
            return {"answer": answer}

        if "view" in intent or "show application" in query.lower():
            answer = self.workflow_service.view_application(session_id, self.db)
            return {"answer": answer}

        if "update" in intent or "change" in query.lower():
            try:
                updates_str = query.split("update", 1)[1]
                updates_str = updates_str.replace(",", " and ")
                updates_list = [u.strip() for u in updates_str.split(" and ") if u.strip()]
                field_aliases = {
                    "mail": "email",
                    "role": "job_role",
                    "company name": "company"
                }
                messages = []
                for item in updates_list:
                    if "to" not in item:
                        messages.append(f"⚠️ Could not understand: '{item}'")
                        continue
                    field_part, value_part = item.split("to", 1)
                    field = field_part.replace("my", "").replace("the", "").strip()
                    if field in field_aliases:
                        field = field_aliases[field]
                    value = value_part.strip()
                    result = self.workflow_service.update_application(session_id, self.db, field, value)
                    messages.append(result)
                return {"answer": "\n".join(messages)}
            except Exception as e:
                return {"answer": f"❌ Could not parse update command: {e}"}

        if "delete" in intent or "remove" in query.lower():
            answer = self.workflow_service.delete_application(session_id, self.db)
            return {"answer": answer}

        answer = self.get_answer(query, history).get("answer")
        return {"answer": answer}

    def check_intent(self, query: str):
        prompt = f"""
            User message: {query}

            Identify the user's intent for job application management.
            Possible intents:
            - start: start a new job application
            - view: view submitted application details
            - update: update specific fields in an existing application
            - delete: delete or remove the application
            - none: unrelated to job application

            Reply in JSON: {{"action": "<one_of_above>"}}
            """
        result = self.rag_service.fallback_llm.invoke([HumanMessage(content=prompt)])
        return result.content

    def get_answer(self, query: str, history: list = None):
        return self.rag_service.get_answer(query, history)