from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from db.database import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    state = Column(String, default="APPLICATION_STARTED")
    name = Column(String)
    email = Column(String)
    company = Column(String)
    job_role = Column(String)
    experience = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)