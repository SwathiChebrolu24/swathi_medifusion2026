import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine

def add_columns():
    with engine.connect() as conn:
        try:
            # Add columns to patient_cases
            conn.execute(text("ALTER TABLE patient_cases ADD COLUMN severity_score FLOAT;"))
            conn.execute(text("ALTER TABLE patient_cases ADD COLUMN doctor_notes VARCHAR;"))
            conn.execute(text("ALTER TABLE patient_cases ADD COLUMN diagnosis VARCHAR;"))
            conn.execute(text("ALTER TABLE patient_cases ADD COLUMN reviewed_by_doctor BOOLEAN DEFAULT FALSE;"))
            print("✅ Added columns to patient_cases table.")
        except Exception as e:
            print(f"⚠️ Error adding columns to patient_cases (might exist): {e}")

        try:
            # Add columns to users
            conn.execute(text("ALTER TABLE users ADD COLUMN specialty VARCHAR;"))
            print("✅ Added columns to users table.")
        except Exception as e:
            print(f"⚠️ Error adding columns to users (might exist): {e}")
            
        conn.commit()

if __name__ == "__main__":
    add_columns()
