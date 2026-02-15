import sys
import os

# Add the parent directory to sys.path to allow importing 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import Base, engine, SessionLocal
from app.workers.tasks import process_case_task
from app.models.user import User
from app.models.patient_case import PatientCase
from app.models.reports import Report

# 1️⃣ Create all tables
print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")

# 2️⃣ Test database connection
print("Testing database connection...")
db = SessionLocal()
try:
    result = db.execute(text("SELECT 1")).fetchall()
    print("Database connection test result:", result)
finally:
    db.close()

# 3️⃣ Test Celery task
print("Sending test Celery task...")
task = process_case_task.delay(1)  # replace 1 with actual case ID if exists
print("Task sent! Task ID:", task.id)
print("Check your worker logs to see if the task was executed.")
