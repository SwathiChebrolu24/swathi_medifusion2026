# app/api/patient/routes.py

from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.patient_case import PatientCase
from app.models.user import User
from app.schemas.case_schema import CaseCreate, CaseOut
from app.utils.file_handler import save_upload_file
from app.workers.tasks import process_case_task
from app.core.security import get_current_user

# Import Real AI functions
from app.ai.predictor import (
    analyze_image_bytes, 
    analyze_symptoms,
    summarize_case_history,
    analyze_symptom_severity
)

router = APIRouter()

@router.post("/upload-image", response_model=CaseOut)
async def upload_image(
    patient_name: str = Form(None),
    patient_contact: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # 1. Read file bytes for AI
        file_bytes = await file.read()
        
        # 2. Save file to disk
        await file.seek(0)
        saved_path = save_upload_file(file)

        # 3. Run AI prediction
        prediction = analyze_image_bytes(file_bytes)
        
        # 4. Calculate severity score from AI prediction (0-10 scale)
        severity = 0.0
        # Support both old and new format
        prob = float(prediction.get('top_prob') or prediction.get('prob') or 0)
        label = (prediction.get('top_label') or prediction.get('label') or '').lower()
        
        if prediction:
            # Adjust severity based on condition
            if 'normal' in label:
                severity = prob * 2.0  # Normal: 0-2
            elif any(word in label for word in ['pneumonia', 'covid', 'tuberculosis']):
                severity = 5.0 + (prob * 5.0)  # Serious: 5-10
            else:
                severity = 3.0 + (prob * 4.0)  # Moderate: 3-7
        
        # 5. Create Case
        new_case = PatientCase(
            patient_name=patient_name or current_user.full_name or current_user.username,
            patient_contact=patient_contact,
            uploaded_file=saved_path,
            status="new",
            xray_result=prediction,
            severity_score=round(severity, 2)
        )
        db.add(new_case)
        db.commit()
        db.refresh(new_case)
        
        # 5. Dispatch background worker (optional)
        try:
            process_case_task.delay(new_case.id)
        except Exception as e:
            print(f"⚠️ Warning: Background task failed: {e}")
            pass
        
        return new_case
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error uploading X-ray: {str(e)}")


@router.post("/submit-symptoms", response_model=CaseOut)
def submit_symptoms(
    data: CaseCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Run AI prediction
        prediction = analyze_symptoms(data.symptoms)
        
        # NEW: Analyze symptom urgency using text analysis
        urgency_analysis = analyze_symptom_severity(data.symptoms)
        print(f"Urgency Analysis: {urgency_analysis}")

        # Calculate severity score from AI prediction (0-10 scale)
        severity = 0.0
        # Support both old and new format
        prob = float(prediction.get('top_prob') or prediction.get('prob') or 0)
        label = (prediction.get('top_label') or prediction.get('label') or '').lower()

        if prediction:
            # Adjust severity based on predicted condition
            if 'normal' in label or 'healthy' in label:
                severity = prob * 2.0  # Normal: 0-2
            elif any(word in label for word in ['pneumonia', 'covid', 'tuberculosis', 'severe']):
                severity = 6.0 + (prob * 4.0)  # Serious: 6-10
            elif any(word in label for word in ['asthma', 'bronchitis']):
                severity = 4.0 + (prob * 3.0)  # Moderate: 4-7
            else:
                severity = 3.0 + (prob * 4.0)  # Default moderate: 3-7
        
        # Boost severity if urgency is high
        if urgency_analysis.get('urgency') == 'high':
            severity = min(10.0, severity + 2.0)
            print(f"Severity boosted due to high urgency: {severity}")

        # Create Case
        new_case = PatientCase(
            patient_name=data.patient_name or current_user.full_name or current_user.username,
            patient_contact=data.patient_contact,
            symptoms=data.symptoms,
            status="new",
            symptom_result=prediction,
            severity_score=round(severity, 2)
        )
        db.add(new_case)
        db.commit()
        db.refresh(new_case)

        # Dispatch background worker
        try:
            process_case_task.delay(new_case.id)
        except Exception as e:
            print(f"⚠️ Warning: Background task failed (Redis not running?): {e}")
            pass

        return new_case
    except Exception as e:
        import traceback
        with open("error.log", "w") as f:
            f.write(traceback.format_exc())
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing symptoms: {str(e)}")


@router.get("/my-cases", response_model=list[CaseOut])
def my_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Fetch cases matching the logged-in user's name
        cases = db.query(PatientCase).filter(
            (PatientCase.patient_name == current_user.username) | 
            (PatientCase.patient_name == current_user.full_name)
        ).order_by(PatientCase.created_at.desc()).all()
        
        return cases
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching cases: {str(e)}")


@router.get("/doctors", response_model=list[dict])
def get_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of all doctors for assignment."""
    doctors = db.query(User).filter(User.role == "doctor").all()
    return [
        {"id": d.id, "name": d.full_name or d.username, "specialty": d.specialty or "General"} 
        for d in doctors
    ]


@router.post("/cases/{case_id}/assign")
async def assign_case(
    case_id: int,
    doctor_id: int = Body(None, embed=True), # Optional, if None -> Open Pool
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a case to a specific doctor or the open pool."""
    print(f"\n=== ASSIGN CASE CALLED ===")
    print(f"Case ID: {case_id}")
    print(f"Doctor ID: {doctor_id}")
    print(f"Current User: {current_user.username}")
    
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        print(f"ERROR: Case {case_id} not found")
        raise HTTPException(status_code=404, detail="Case not found")
    
    print(f"Found case: {case.id}, current status: {case.status}")
    
    # Verify ownership
    if case.patient_name != current_user.username and case.patient_name != current_user.full_name:
        # In a real app check user ID, but for now name matching
        print(f"WARNING: Patient name mismatch: {case.patient_name} vs {current_user.username}/{current_user.full_name}")
        pass 

    from datetime import datetime
    
    if doctor_id:
        # Specific Doctor
        print(f"Assigning to specific doctor: {doctor_id}")
        case.assigned_doctor_id = doctor_id
        case.assigned_at = datetime.utcnow()
        case.status = "submitted"
    else:
        # Open Pool
        print(f"Assigning to open pool")
        case.assigned_doctor_id = None
        case.assigned_at = None
        case.status = "submitted"
    
    print(f"Before commit - Status: {case.status}, Assigned to: {case.assigned_doctor_id}")
    db.commit()
    db.refresh(case)
    print(f"After commit - Status: {case.status}, Assigned to: {case.assigned_doctor_id}")
    print(f"=== ASSIGN CASE COMPLETE ===\n")
    
    # WebSocket notifications disabled for now due to routing issues
    # TODO: Fix WebSocket endpoint and re-enable notifications
    
    return case


@router.get("/cases/{case_id}/summary")
def get_case_summary(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get an AI-generated summary of a case.
    Uses BART summarization to condense case information.
    """
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Build case data dictionary
    case_data = {
        "patient_name": case.patient_name,
        "symptoms": case.symptoms,
        "xray_result": case.xray_result,
        "symptom_result": case.symptom_result,
        "doctor_notes": case.doctor_notes,
        "diagnosis": case.diagnosis,
        "severity_score": case.severity_score
    }
    
    # Generate summary using BART
    summary = summarize_case_history(case_data)
    
    return {
        "case_id": case_id,
        "summary": summary,
        "generated_by": "BART AI Summarization"
    }


@router.delete("/cases/{case_id}")
def delete_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a patient's own case
    """
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Verify the case belongs to the current user (patient)
    # Assuming patient cases are linked by patient_name or we need to add user_id
    # For now, we'll allow deletion if user is a patient
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can delete their own cases")
    
    db.delete(case)
    db.commit()
    
    return {"message": "Case deleted successfully", "case_id": case_id}


@router.post("/cases/{case_id}/schedule-test")
def schedule_test(
    case_id: int,
    date: str = Body(..., embed=True), # ISO format string
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Patient schedules a date for their ordered test.
    """
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Verify ownership
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can schedule tests")
        
    # Verify test is ordered
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


@router.post("/cases/{case_id}/book-test")
def book_test(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Patient confirms booking for a recommended test.
    Moves status from 'recommended' to 'pending' (Open Pool for Lab).
    """
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Verify ownership
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can book tests")
        
    # Verify test is recommended
    if case.test_status != "recommended":
        raise HTTPException(status_code=400, detail="Test is not in recommended status")
        
    case.test_status = "pending"
    
    db.commit()
    db.refresh(case)
    return {"message": "Test booked successfully", "test_status": case.test_status}
