from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.patient_case import PatientCase
from app.models.user import User
from app.schemas.case_schema import CaseOut
from app.utils.security import require_role
from app.core.security import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class DoctorDashboardData(BaseModel):
    my_cases: list[CaseOut]
    open_pool: list[CaseOut]
    closed_cases: list[CaseOut]

@router.get("/assigned", response_model=DoctorDashboardData, dependencies=[Depends(require_role("doctor"))])
def assigned_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get cases assigned to the doctor AND open pool cases.
    Also handles auto-reassignment logic (lazy check).
    """
    from datetime import datetime, timedelta
    
    # 1. Auto-Reassignment Logic (Lazy Check)
    # Find cases assigned to ANY doctor that have expired (> 15 mins) and not reviewed
    timeout_threshold = datetime.utcnow() - timedelta(minutes=15)
    expired_cases = db.query(PatientCase).filter(
        PatientCase.assigned_doctor_id.isnot(None),
        PatientCase.reviewed_by_doctor == False,
        PatientCase.assigned_at < timeout_threshold
    ).all()
    
    for case in expired_cases:
        case.assigned_doctor_id = None # Move back to pool
        case.assigned_at = None
    
    if expired_cases:
        db.commit()
        
    # 2. Fetch My Assignments
    my_cases = db.query(PatientCase).filter(
        PatientCase.assigned_doctor_id == current_user.id,
        PatientCase.reviewed_by_doctor == False
    ).order_by(PatientCase.created_at.desc()).all()
    
    # 3. Fetch Open Pool (Unassigned AND Submitted)
    open_pool = db.query(PatientCase).filter(
        PatientCase.assigned_doctor_id == None,
        PatientCase.status == "submitted",
        PatientCase.reviewed_by_doctor == False
    ).order_by(PatientCase.created_at.desc()).all()
    
    # 4. Fetch Closed Cases (Reviewed by me)
    closed_cases = db.query(PatientCase).filter(
        PatientCase.assigned_doctor_id == current_user.id,
        PatientCase.reviewed_by_doctor == True
    ).order_by(PatientCase.updated_at.desc()).all()
    
    return {
        "my_cases": my_cases,
        "open_pool": open_pool,
        "closed_cases": closed_cases
    }


@router.post("/cases/{case_id}/accept", response_model=CaseOut, dependencies=[Depends(require_role("doctor"))])
async def accept_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept a case from the open pool."""
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if case.assigned_doctor_id is not None:
        raise HTTPException(status_code=400, detail="Case already assigned")
        
    from datetime import datetime
    case.assigned_doctor_id = current_user.id
    case.assigned_at = datetime.utcnow()
    
    db.commit()
    db.refresh(case)
    
    # Send WebSocket notification to patient
    from app.core.websocket_manager import manager
    try:
        # Find patient user by name
        logger.info(f"Looking for patient user with username: '{case.patient_name}'")
        patient_user = db.query(User).filter(User.username == case.patient_name).first()
        if patient_user:
            logger.info(f"Found patient user: {patient_user.username} (ID: {patient_user.id})")
            await manager.send_personal_message({
                "type": "case_update",
                "message": f"Your case has been accepted by Dr. {current_user.full_name or current_user.username}"
            }, patient_user.id)
            logger.info(f"✅ WebSocket notification sent to patient {patient_user.id}")
        else:
            logger.warning(f"❌ Patient user not found for case {case.id}, patient_name='{case.patient_name}'")
            # Try to find by full_name as fallback
            patient_user = db.query(User).filter(User.full_name == case.patient_name).first()
            if patient_user:
                logger.info(f"Found patient by full_name: {patient_user.username} (ID: {patient_user.id})")
                await manager.send_personal_message({
                    "type": "case_update",
                    "message": f"Your case has been accepted by Dr. {current_user.full_name or current_user.username}"
                }, patient_user.id)
                logger.info(f"✅ WebSocket notification sent to patient {patient_user.id}")
    except Exception as e:
        logger.error(f"❌ WebSocket notification failed: {e}", exc_info=True)
    
    return case


@router.get("/stats", dependencies=[Depends(require_role("doctor"))])
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get doctor statistics."""
    print(f"\n=== STATS ENDPOINT CALLED ===")
    print(f"Current user: {current_user.username}, Role: {current_user.role}")
    
    # Total cases reviewed by THIS doctor
    closed_count = db.query(PatientCase).filter(
        PatientCase.assigned_doctor_id == current_user.id,
        PatientCase.reviewed_by_doctor == True
    ).count()
    
    print(f"Closed count: {closed_count}")
    print(f"=== STATS ENDPOINT COMPLETE ===\n")
    
    return {"total_cases_closed": closed_count}


@router.post("/review/{case_id}", response_model=CaseOut, dependencies=[Depends(require_role("doctor"))])
async def review_case(
    case_id: int, 
    notes: str = Body(...), 
    diagnosis: str = Body(None),
    severity_score: float = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="case not found")
    
    # Ensure doctor is assigned
    if case.assigned_doctor_id != current_user.id:
         raise HTTPException(status_code=403, detail="Not assigned to this case")
    
    # Prevent duplicate submission
    if case.reviewed_by_doctor:
        raise HTTPException(status_code=400, detail="Case already reviewed. Cannot submit again.")

    case.doctor_notes = notes
    if diagnosis:
        case.diagnosis = diagnosis
    if severity_score is not None:
        case.severity_score = severity_score
        
    # Mark case as reviewed and completed
    # Only keep open if test was explicitly ordered AND is still pending
    if case.test_ordered == True and case.test_status == "pending":
        # Keep case open for lab results
        case.reviewed_by_doctor = False
        case.status = "waiting_lab"
    else:
        # Close the case
        case.reviewed_by_doctor = True
        case.status = "completed"
    
    db.add(case)
    db.commit()
    db.refresh(case)
    
    # Send WebSocket notification to patient
    from app.core.websocket_manager import manager
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Find patient user by name
        patient_user = db.query(User).filter(User.username == case.patient_name).first()
        if patient_user:
            if case.reviewed_by_doctor:
                await manager.send_personal_message({
                    "type": "case_update",
                    "message": f"Your case has been reviewed. Diagnosis: {case.diagnosis or 'See details'}"
                }, patient_user.id)
            else:
                await manager.send_personal_message({
                    "type": "case_update",
                    "message": "Your case review is pending lab results"
                }, patient_user.id)
            logger.info(f"WebSocket notification sent to patient {patient_user.id}")
        else:
            logger.warning(f"Patient user not found for case {case.id}")
    except Exception as e:
        logger.error(f"WebSocket notification failed: {e}")
    
    return case


@router.post("/cases/{case_id}/order-test", response_model=CaseOut, dependencies=[Depends(require_role("doctor"))])
def order_test(
    case_id: int,
    test_type: str = Body(..., embed=True), # e.g. "X-Ray"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Order a test for a patient case."""
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Ensure doctor is assigned
    if case.assigned_doctor_id != current_user.id:
         raise HTTPException(status_code=403, detail="Not assigned to this case")

    case.test_ordered = True
    case.ordered_test_type = test_type
    case.test_status = "recommended"
    
    db.commit()
    db.refresh(case)
    return case
