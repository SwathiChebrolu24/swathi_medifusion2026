
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime

class CaseCreate(BaseModel):
    patient_name: str
    patient_contact: Optional[str]
    symptoms: Optional[str]

class CaseOut(BaseModel):
    id: int
    patient_name: str
    patient_contact: Optional[str]
    uploaded_file: Optional[str]
    symptoms: Optional[str]
    xray_result: Optional[Dict]       # Matches Case.xray_result
    symptom_result: Optional[Dict]    # Matches Case.symptom_result
    status: str
    created_at: datetime              # When case was created
    severity_score: Optional[float]   # AI-generated severity (0-10)
    doctor_notes: Optional[str]       # Doctor's review notes
    diagnosis: Optional[str]          # Final diagnosis
    reviewed_by_doctor: Optional[bool] # Review status
    assigned_doctor_id: Optional[int]
    assigned_at: Optional[datetime]
    
    # Lab Fields
    test_status: Optional[str]
    assigned_lab_tech_id: Optional[int]
    lab_notes: Optional[str] = None
    report_file: Optional[str] = None
    test_ordered: bool = False
    ordered_test_type: Optional[str] = None

    class Config:
        orm_mode = True
