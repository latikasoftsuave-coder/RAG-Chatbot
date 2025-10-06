from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import urllib.parse

POSTGRES_USER = os.getenv("POSTGRES_USER", "latika")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "Latika@13")
POSTGRES_DB = os.getenv("POSTGRES_DB", "rag_chatbot")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

POSTGRES_PASSWORD_ENC = urllib.parse.quote_plus(POSTGRES_PASSWORD)

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD_ENC}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()