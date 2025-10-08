from db.models import JobApplication
from sqlalchemy.orm import Session

application_sessions = {}

class ApplicationService:
    required_fields = ["name", "email", "company", "job_role", "experience"]

    def start_application(self, session_id: str):
        application_sessions[session_id] = {
            "state": "APPLICATION_STARTED",
            "data": {field: None for field in self.required_fields}
        }
        return "Let's start your job application! Please provide your name:"

    def get_session(self, session_id: str):
        return application_sessions.get(session_id)

    def update_field(self, session_id: str, field: str, value: str):
        session = self.get_session(session_id)
        if not session:
            return False
        if not value or value.strip().lower() == "null":
            value = None
        else:
            value = value.strip()
        session["data"][field] = value
        all_filled = all(session["data"].get(f) not in [None, ""] for f in self.required_fields)
        if all_filled:
            session["state"] = "AWAITING_CONFIRMATION"
        return True

    def next_missing_field(self, session_id: str):
        session = self.get_session(session_id)
        if not session:
            return None
        for field in self.required_fields:
            if not session["data"].get(field):
                return field
        return None

    def confirm_application(self, session_id: str, db: Session):
        session = self.get_session(session_id)
        if not session:
            return "No active application found."
        data = session["data"]
        for k, v in data.items():
            if v is not None:
                data[k] = str(v).strip()
            else:
                data[k] = None
        try:
            existing_app = db.query(JobApplication).filter(JobApplication.session_id == session_id).first()
            if existing_app:
                existing_app.name = data.get("name")
                existing_app.email = data.get("email")
                existing_app.company = data.get("company")
                existing_app.job_role = data.get("job_role")
                existing_app.experience = data.get("experience")
            else:
                job_app = JobApplication(
                    session_id=session_id,
                    name=data.get("name"),
                    email=data.get("email"),
                    company=data.get("company"),
                    job_role=data.get("job_role"),
                    experience=data.get("experience"),
                )
                db.add(job_app)
            db.commit()
            del application_sessions[session_id]
            message = (
                f"✅ Application confirmed and submitted successfully!\n\n"
                f"Name: {data.get('name')}\n\n"
                f"Email: {data.get('email')}\n\n"
                f"Company: {data.get('company')}\n\n"
                f"Job Role: {data.get('job_role')}\n\n"
                f"Experience: {data.get('experience')}"
            )
            return message
        except Exception as e:
            db.rollback()
            return f"❌ Failed to confirm application: {e}"

    def cancel_application(self, session_id: str):
        if session_id in application_sessions:
            del application_sessions[session_id]
        return "Application canceled."

    def view_application(self, session_id: str, db: Session):
        app = db.query(JobApplication).filter(JobApplication.session_id == session_id).first()
        if not app:
            return "❌ No application found for your session."
        return (
            f"📄 Here are your application details:\n\n"
            f"Name: {app.name or 'N/A'}\n\n"
            f"Email: {app.email or 'N/A'}\n\n"
            f"Company: {app.company or 'N/A'}\n\n"
            f"Job Role: {app.job_role or 'N/A'}\n\n"
            f"Experience: {app.experience or 'N/A'}"
        )

    def update_application(self, session_id: str, db: Session, field: str, value: str):
        app = db.query(JobApplication).filter(JobApplication.session_id == session_id).first()
        if not app:
            return "❌ No existing application found to update."
        if field not in self.required_fields:
            return f"⚠️ '{field}' is not a valid field. Valid fields are: {', '.join(self.required_fields)}"
        setattr(app, field, value.strip())
        db.commit()
        db.refresh(app)
        return f"✅ Your {field} has been updated to '{value.strip()}'.\n"

    def delete_application(self, session_id: str, db: Session):
        app = db.query(JobApplication).filter(JobApplication.session_id == session_id).first()
        if not app:
            return "❌ No application found to delete."
        db.delete(app)
        db.commit()
        return "🗑️ Your job application has been permanently deleted."