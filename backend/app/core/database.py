# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import os

# Read DATABASE_URL from env; fallback to SQLite for local development
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./medifusion.db"
)

# echo=True while developing is useful (SQL printed). Turn off in prod.
# For SQLite, add connect_args to handle threading
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, future=True, connect_args=connect_args)

# SessionLocal class
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)

# Base for models
Base = declarative_base()

# Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
