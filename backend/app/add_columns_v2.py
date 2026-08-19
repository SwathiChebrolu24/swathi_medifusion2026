import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine

def add_columns():
    with engine.connect() as conn:
        # Add patient_cases columns individually so reruns are safe
        for column_name, column_def in (
            ("severity_score", "FLOAT"),
            ("doctor_notes", "VARCHAR"),
            ("diagnosis", "VARCHAR"),
            ("reviewed_by_doctor", "BOOLEAN DEFAULT FALSE"),
            ("user_id", "INTEGER")
        ):
            try:
                conn.execute(text(f"ALTER TABLE patient_cases ADD COLUMN {column_name} {column_def};"))
                print(f"✅ Added patient_cases.{column_name} column.")
            except Exception as e:
                print(f"⚠️ Error adding patient_cases.{column_name} (might exist): {e}")

        for column_name, column_type in (("specialty", "VARCHAR"), ("otp_created_at", "DATETIME")):
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type};"))
                print(f"✅ Added users.{column_name} column.")
            except Exception as e:
                print(f"⚠️ Error adding users.{column_name} (might exist): {e}")
            
        conn.commit()

if __name__ == "__main__":
    add_columns()
