# app/core/init_db.py
from app.models.user import User
from app.core.database import Base, engine

# ✅ IMPORT ALL MODELS
from app.models.user import User
from app.models.patient_case import PatientCase
from app.models.reports import Report

def init():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")

if __name__ == "__main__":
    init()
