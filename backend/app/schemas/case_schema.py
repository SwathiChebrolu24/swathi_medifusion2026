from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class CaseCreate(BaseModel):
    patient_name: str
    patient_contact: Optional[str] = None
    symptoms: Optional[str] = None


class CaseOut(BaseModel):
    id: int
    patient_name: str
    patient_contact: Optional[str] = None
    uploaded_file: Optional[str] = None
    symptoms: Optional[str] = None
    xray_result: Optional[Dict[str, Any]] = None
    symptom_result: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    severity_score: Optional[float] = None
    doctor_notes: Optional[str] = None
    diagnosis: Optional[str] = None
    reviewed_by_doctor: Optional[bool] = False
    assigned_doctor_id: Optional[int] = None
    assigned_at: Optional[datetime] = None
    user_id: Optional[int] = None

    # Lab Fields
    test_status: Optional[str] = None
    assigned_lab_tech_id: Optional[int] = None
    lab_notes: Optional[str] = None
    report_file: Optional[str] = None
    test_ordered: bool = False
    ordered_test_type: Optional[str] = None
    scheduled_date: Optional[datetime] = None

    model_config = {"from_attributes": True}  # Pydantic v2 syntax (replaces orm_mode = True)
