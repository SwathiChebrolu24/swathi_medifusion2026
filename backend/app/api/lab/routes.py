from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.patient_case import PatientCase
from app.models.user import User
from app.models.lab_models import LabComment, LabReport
from app.schemas.case_schema import CaseOut
from app.core.security import get_current_user
from app.utils.security import require_role
from app.utils.security import require_role
from app.utils.file_handler import save_upload_file
from app.ai.predictor import analyze_image_bytes

router = APIRouter()

# --------------------------
# Patient Management
# --------------------------

@router.get("/patients", response_model=List[CaseOut], dependencies=[Depends(require_role("lab_tech"))])
def get_all_patients(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all patients/cases for the lab dashboard.
    If search is provided, searches Users by username/name and returns their cases.
    If a user is found but has no cases, returns a placeholder case.
    """
    if search:
        search_term = f"%{search}%"
        # Find matching patients (Users)
        users = db.query(User).filter(
            User.role == "patient",
            (User.username.ilike(search_term)) | (User.full_name.ilike(search_term))
        ).all()
        
        # Return user info as virtual cases for display
        results = []
        for user in users:
            virtual_case = PatientCase(
                id=0,  # Virtual ID (not saved to DB)
                patient_name=f"{user.full_name or user.username} ({user.username})",  # Include username for frontend
                patient_contact=user.email,
                status="search_result",
                test_status="Ready for Upload",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                test_ordered=False,
                uploaded_file=None,
                symptoms=None,
                xray_result=None,
                symptom_result=None,
                severity_score=0.0,
                doctor_notes=None,
                diagnosis=None,
                reviewed_by_doctor=False,
                assigned_doctor_id=None,
                assigned_at=None,
                assigned_lab_tech_id=None,
                lab_notes=None,
                report_file=None,
                ordered_test_type=None,
                scheduled_date=None
            )
            # Store username in a custom attribute for upload
            virtual_case.username = user.username
            results.append(virtual_case)
                
        return results
        
    else:
        # Default: Show empty state (user must search)
        return []

@router.get("/my-tasks", response_model=List[CaseOut], dependencies=[Depends(require_role("lab_tech"))])
def get_my_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get cases assigned specifically to this lab technician.
    """
    cases = db.query(PatientCase).filter(
        PatientCase.assigned_lab_tech_id == current_user.id
    ).order_by(PatientCase.created_at.desc()).all()
    return cases

@router.post("/upload-document")
async def upload_document(
    username: str = Form(...),
    doc_type: str = Form(...),
    notes: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a document for a patient (creates a new case if needed)."""
    # Check role
    if current_user.role not in ["lab_tech", "admin", "lab", "labor"]:
         raise HTTPException(status_code=403, detail="Not authorized")

    # Find patient
    patient = db.query(User).filter(User.username == username, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Save file
    file_path = save_upload_file(file)

    # Create Case
    new_case = PatientCase(
        patient_name=patient.full_name or patient.username,
        patient_contact=patient.email,
        uploaded_file=file_path if doc_type == "xray" else None,
        report_file=file_path if doc_type != "xray" else None,
        status="completed",
        test_status="completed",
        test_ordered=True,
        ordered_test_type=doc_type,
        lab_notes=notes,
        assigned_lab_tech_id=current_user.id,
        created_at=datetime.utcnow()
    )
    
    # If X-ray, run AI
    if doc_type == "xray" or file.content_type.startswith("image/"):
        try:
            # Read file from disk
            import os
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                
                prediction = analyze_image_bytes(file_bytes)
                new_case.xray_result = prediction
                
                # Calculate severity
                prob = float(prediction.get('top_prob') or prediction.get('prob') or 0)
                label = (prediction.get('top_label') or prediction.get('label') or '').lower()
                severity = 0.0
                if 'normal' in label:
                    severity = prob * 2.0
                elif any(word in label for word in ['pneumonia', 'covid', 'tuberculosis']):
                    severity = 5.0 + (prob * 5.0)
                else:
                    severity = 3.0 + (prob * 4.0)
                
                new_case.severity_score = round(severity, 2)
                new_case.lab_notes = (new_case.lab_notes or "") + f"\n[AI Analysis]: {label} ({prob}%)"
        except Exception as e:
            print(f"Error running AI on upload: {e}")

    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    
    return {"status": "success", "case_id": new_case.id}

# --------------------------
# Test Workflow
# --------------------------

@router.put("/cases/{case_id}/status")
def update_test_status(
    case_id: int,
    status: str = Body(..., embed=True), # pending, in_progress, completed
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the status of a lab test."""
    # Check role (allow lab_tech or admin)
    if current_user.role not in ["lab_tech", "admin", "lab", "labor"]:
         raise HTTPException(status_code=403, detail="Not authorized")

    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    case.test_status = status
    
    # If completed, maybe notify doctor? (Future feature)
    
    db.commit()
    db.refresh(case)
    return {"status": "success", "case_id": case.id, "new_status": case.test_status}

@router.post("/cases/{case_id}/assign")
def assign_test(
    case_id: int,
    lab_tech_id: int = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a test to a specific lab technician."""
    # Check role
    if current_user.role not in ["lab_tech", "admin", "lab", "labor"]:
         raise HTTPException(status_code=403, detail="Not authorized")

    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    case.assigned_lab_tech_id = lab_tech_id
    case.test_status = "in_progress" # Auto-move to in progress
    
    db.commit()
    db.refresh(case)
    return {"status": "success", "assigned_to": lab_tech_id}

# --------------------------
# Report Management
# --------------------------

@router.post("/cases/{case_id}/notes")
def add_lab_notes(
    case_id: int,
    notes: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add technical notes to a case."""
    if current_user.role not in ["lab_tech", "admin", "lab", "labor"]:
         raise HTTPException(status_code=403, detail="Not authorized")

    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Append notes or overwrite? Let's overwrite for simple field, 
    # or append to comment table for history.
    # Using the simple column for now as per schema
    case.lab_notes = notes
    
    # Also add to history table
    new_comment = LabComment(
        case_id=case_id,
        lab_tech_id=current_user.id,
        comment=notes
    )
    db.add(new_comment)
    
    db.commit()
    return {"status": "success", "notes": notes}

@router.post("/cases/{case_id}/upload-report")
async def upload_lab_report(
    case_id: int,
    file: UploadFile = File(...),
    report_type: str = Form("pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a formal lab report file."""
    if current_user.role not in ["lab_tech", "admin", "lab", "labor"]:
         raise HTTPException(status_code=403, detail="Not authorized")

    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Save file
    file_path = save_upload_file(file)
    
    # Update case
    case.report_file = file_path
    case.test_status = "completed" # Auto-complete
    
    # TRIGGER AI if it is an image
    if report_type == "xray" or file.content_type.startswith("image/"):
        try:
            # Read file again (save_upload_file might have closed it, or we need to read from path)
            # Since save_upload_file saves it to disk, let's read from disk or seek 0 if possible.
            # Ideally we should have read bytes before saving.
            # Let's read from the saved path.
            import os
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                
                prediction = analyze_image_bytes(file_bytes)
                case.xray_result = prediction
                
                # Calculate severity (reusing logic from patient routes - ideally refactor to util)
                prob = float(prediction.get('top_prob') or prediction.get('prob') or 0)
                label = (prediction.get('top_label') or prediction.get('label') or '').lower()
                severity = 0.0
                if 'normal' in label:
                    severity = prob * 2.0
                elif any(word in label for word in ['pneumonia', 'covid', 'tuberculosis']):
                    severity = 5.0 + (prob * 5.0)
                else:
                    severity = 3.0 + (prob * 4.0)
                
                case.severity_score = round(severity, 2)
                case.lab_notes = (case.lab_notes or "") + f"\n[AI Analysis]: {label} ({prob}%)"
        except Exception as e:
            print(f"Error running AI on lab upload: {e}")

    # Add to report history
    new_report = LabReport(
        case_id=case_id,
        report_type=report_type,
        file_path=file_path,
        uploaded_by=current_user.id
    )
    db.add(new_report)
    
    db.commit()
    return {"status": "success", "file_path": file_path, "ai_triggered": True}

@router.post("/reports/manual")
def submit_manual_report(
    case_id: int = Body(..., embed=True),
    data: str = Body(..., embed=True), # JSON string or formatted text
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit a manual test result."""
    if current_user.role not in ["lab_tech", "admin", "lab", "labor"]:
         raise HTTPException(status_code=403, detail="Not authorized")

    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Create report entry
    new_report = LabReport(
        case_id=case_id,
        report_type="manual",
        manual_data=data,
        uploaded_by=current_user.id
    )
    db.add(new_report)
    
    # Update case status
    case.test_status = "completed"
    case.lab_notes = f"Manual Result: {data[:50]}..." # Preview in notes
    
    db.commit()
    return {"status": "success", "report_id": new_report.id}

@router.get("/patients/{patient_id}/history")
def get_patient_history(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed history for a patient."""
    if current_user.role not in ["lab_tech", "admin", "lab", "labor"]:
         raise HTTPException(status_code=403, detail="Not authorized")

    # Assuming patient_id refers to the User ID of the patient? 
    # Or do we filter by patient_name? 
    # In this simple app, we don't have a separate Patient table, just Users with role='patient'.
    # But PatientCase has 'patient_id' which is the User ID.
    
    cases = db.query(PatientCase).filter(PatientCase.patient_id == patient_id).order_by(PatientCase.created_at.desc()).all()
    return cases
