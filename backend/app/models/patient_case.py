from sqlalchemy import Column, Integer, String, JSON, Float, Boolean, DateTime, ForeignKey
from datetime import datetime
from .base import Base


class PatientCase(Base):
    __tablename__ = "patient_cases"

    id = Column(Integer, primary_key=True, index=True)

    # Patient ownership — proper FK link (replaces fragile name matching)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    patient_name = Column(String, nullable=False)
    patient_contact = Column(String, nullable=True)
    uploaded_file = Column(String, nullable=True)
    symptoms = Column(String, nullable=True)
    status = Column(String, default="new")  # new | submitted | completed | waiting_lab

    # AI Results
    xray_result = Column(JSON, nullable=True)
    symptom_result = Column(JSON, nullable=True)

    # Doctor Review
    severity_score = Column(Float, nullable=True, default=0.0)
    doctor_notes = Column(String, nullable=True)
    diagnosis = Column(String, nullable=True)
    reviewed_by_doctor = Column(Boolean, default=False)

    # Doctor Assignment
    assigned_doctor_id = Column(Integer, nullable=True)
    assigned_at = Column(DateTime, nullable=True)

    # Lab Fields
    test_status = Column(String, default="pending")         # pending | recommended | scheduled | in_progress | completed
    assigned_lab_tech_id = Column(Integer, nullable=True)
    lab_notes = Column(String, nullable=True)
    report_file = Column(String, nullable=True)

    # Test Orders
    test_ordered = Column(Boolean, default=False)
    ordered_test_type = Column(String, nullable=True)       # e.g. "X-Ray", "Blood Test"
    scheduled_date = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
