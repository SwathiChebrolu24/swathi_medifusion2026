# app/api/patient/routes.py

from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.patient_case import PatientCase
from app.models.user import User
from app.schemas.case_schema import CaseCreate, CaseOut
from app.utils.file_handler import save_file_bytes
from app.workers.tasks import process_case_task
from app.core.security import get_current_user
import logging

from app.ai.predictor import (
    analyze_image_bytes,
    analyze_symptoms,
    summarize_case_history,
    analyze_symptom_severity
)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────
# Upload X-Ray Image
# ─────────────────────────────────────────
@router.post("/upload-image", response_model=CaseOut)
async def upload_image(
    patient_name: str = Form(None),
    patient_contact: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # 1. Read bytes once (async-safe)
        file_bytes = await file.read()
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP image")
        if not file_bytes:
            raise HTTPException(status_code=400, detail="The uploaded image is empty")
        if len(file_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller")

        # 2. Save bytes to disk properly
        saved_path = save_file_bytes(file_bytes, file.filename or "upload.jpg")

        # 3. Run AI prediction
        prediction = analyze_image_bytes(file_bytes)

        # 4. Calculate severity score (0–10 scale)
        prob = float(prediction.get('top_prob') or prediction.get('prob') or 0)
        label = (prediction.get('top_label') or prediction.get('label') or '').lower()

        if 'normal' in label:
            severity = prob * 2.0           # Normal: 0–2
        elif any(w in label for w in ['pneumonia', 'covid', 'tuberculosis']):
            severity = 5.0 + (prob * 5.0)  # Serious: 5–10
        else:
            severity = 3.0 + (prob * 4.0)  # Moderate: 3–7

        # 5. Create Case — link to logged-in user
        new_case = PatientCase(
            patient_name=patient_name or current_user.full_name or current_user.username,
            patient_contact=patient_contact,
            uploaded_file=saved_path,
            status="new",
            xray_result=prediction,
            severity_score=round(severity, 2),
            user_id=current_user.id
        )
        db.add(new_case)
        db.commit()
        db.refresh(new_case)

        # 6. Dispatch background worker (optional, graceful fail)
        try:
            process_case_task.delay(new_case.id)
        except Exception as e:
            logger.warning(f"Background task skipped (Redis unavailable?): {e}")

        return new_case

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"X-ray upload error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error uploading X-ray: {str(e)}")


# ─────────────────────────────────────────
# Submit Symptoms
# ─────────────────────────────────────────
@router.post("/submit-symptoms", response_model=CaseOut)
def submit_symptoms(
    data: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        prediction = analyze_symptoms(data.symptoms)
        urgency_analysis = analyze_symptom_severity(data.symptoms)

        prob = float(prediction.get('top_prob') or prediction.get('prob') or 0)
        label = (prediction.get('top_label') or prediction.get('label') or '').lower()

        if 'normal' in label or 'healthy' in label:
            severity = prob * 2.0
        elif any(w in label for w in ['pneumonia', 'covid', 'tuberculosis', 'severe']):
            severity = 6.0 + (prob * 4.0)
        elif any(w in label for w in ['asthma', 'bronchitis']):
            severity = 4.0 + (prob * 3.0)
        else:
            severity = 3.0 + (prob * 4.0)

        # Boost severity for high urgency
        if urgency_analysis.get('urgency') == 'high':
            severity = min(10.0, severity + 2.0)
            logger.info(f"Severity boosted to {severity} due to high urgency")

        new_case = PatientCase(
            patient_name=data.patient_name or current_user.full_name or current_user.username,
            patient_contact=data.patient_contact,
            symptoms=data.symptoms,
            status="new",
            symptom_result=prediction,
            severity_score=round(severity, 2),
            user_id=current_user.id
        )
        db.add(new_case)
        db.commit()
        db.refresh(new_case)

        try:
            process_case_task.delay(new_case.id)
        except Exception as e:
            logger.warning(f"Background task skipped: {e}")

        return new_case

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Symptom submission error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing symptoms: {str(e)}")


# ─────────────────────────────────────────
# My Cases
# ─────────────────────────────────────────
@router.get("/my-cases", response_model=list[CaseOut])
def my_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Filter by user_id (primary) with name fallback for old records
        cases = db.query(PatientCase).filter(
            (PatientCase.user_id == current_user.id) |
            (PatientCase.patient_name == current_user.username) |
            (PatientCase.patient_name == current_user.full_name)
        ).order_by(PatientCase.created_at.desc()).all()
        return cases
    except Exception as e:
        logger.error(f"Error fetching cases: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching cases: {str(e)}")


# ─────────────────────────────────────────
# Get Doctors List
# ─────────────────────────────────────────
@router.get("/doctors", response_model=list[dict])
def get_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of all available doctors."""
    doctors = db.query(User).filter(User.role == "doctor").all()
    return [
        {"id": d.id, "name": d.full_name or d.username, "specialty": d.specialty or "General"}
        for d in doctors
    ]


# ─────────────────────────────────────────
# Assign Case to Doctor
# ─────────────────────────────────────────
@router.post("/cases/{case_id}/assign")
async def assign_case(
    case_id: int,
    doctor_id: int = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a case to a specific doctor or the open pool."""
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Enforce ownership
    if case.user_id and case.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only assign your own cases")

    from datetime import datetime
    if doctor_id:
        case.assigned_doctor_id = doctor_id
        case.assigned_at = datetime.utcnow()
    else:
        case.assigned_doctor_id = None
        case.assigned_at = None

    case.status = "submitted"
    db.commit()
    db.refresh(case)
    logger.info(f"Case {case_id} assigned to doctor {doctor_id} by {current_user.username}")
    return case


# ─────────────────────────────────────────
# Case AI Summary
# ─────────────────────────────────────────
@router.get("/cases/{case_id}/summary")
def get_case_summary(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get an AI-generated summary of a case."""
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case_data = {
        "patient_name": case.patient_name,
        "symptoms": case.symptoms,
        "xray_result": case.xray_result,
        "symptom_result": case.symptom_result,
        "doctor_notes": case.doctor_notes,
        "diagnosis": case.diagnosis,
        "severity_score": case.severity_score
    }
    summary = summarize_case_history(case_data)
    return {"case_id": case_id, "summary": summary, "generated_by": "Gemini AI"}


# ─────────────────────────────────────────
# Delete Case
# ─────────────────────────────────────────
@router.delete("/cases/{case_id}")
def delete_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a patient's own case."""
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if current_user.role != "patient" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only patients can delete their own cases")

    # Enforce ownership
    if current_user.role == "patient":
        if case.user_id and case.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="You can only delete your own cases")

    db.delete(case)
    db.commit()
    return {"message": "Case deleted successfully", "case_id": case_id}


# ─────────────────────────────────────────
# Schedule Test
# ─────────────────────────────────────────
@router.post("/cases/{case_id}/schedule-test")
def schedule_test(
    case_id: int,
    date: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Patient schedules a date for their ordered test."""
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can schedule tests")

    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if not case.test_ordered:
        raise HTTPException(status_code=400, detail="No test has been ordered for this case")

    from datetime import datetime
    try:
        scheduled_dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
        case.scheduled_date = scheduled_dt
        case.test_status = "scheduled"
        db.commit()
        db.refresh(case)
        return {"message": "Test scheduled successfully", "scheduled_date": case.scheduled_date}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO 8601")


# ─────────────────────────────────────────
# Book Test
# ─────────────────────────────────────────
@router.post("/cases/{case_id}/book-test")
def book_test(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Patient confirms booking for a recommended test."""
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can book tests")

    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.test_status != "recommended":
        raise HTTPException(status_code=400, detail="Test is not in 'recommended' status")

    case.test_status = "pending"
    db.commit()
    db.refresh(case)
    return {"message": "Test booked successfully", "test_status": case.test_status}
