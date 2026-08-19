from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.patient_case import PatientCase
from app.models.user import User
from app.core.role_checker import role_required
from app.core.security import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# Import CaseOut for the response model
from app.schemas.case_schema import CaseOut


class DoctorDashboardData(BaseModel):
    my_cases: list[CaseOut]
    open_pool: list[CaseOut]
    closed_cases: list[CaseOut]


@router.get("/assigned", response_model=DoctorDashboardData, dependencies=[Depends(role_required("doctor"))])
def assigned_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get cases assigned to the doctor + open pool.
    Auto-reassigns cases expired (>15 min) back to pool.
    """
    from datetime import datetime, timedelta

    # Auto-Reassignment: expired cases back to pool
    timeout_threshold = datetime.utcnow() - timedelta(minutes=15)
    expired_cases = db.query(PatientCase).filter(
        PatientCase.assigned_doctor_id.isnot(None),
        PatientCase.reviewed_by_doctor == False,
        PatientCase.assigned_at < timeout_threshold
    ).all()

    for case in expired_cases:
        case.assigned_doctor_id = None
        case.assigned_at = None

    if expired_cases:
        db.commit()
        logger.info(f"Auto-reassigned {len(expired_cases)} expired cases to pool")

    # My assigned cases (not yet reviewed)
    my_cases = db.query(PatientCase).filter(
        PatientCase.assigned_doctor_id == current_user.id,
        PatientCase.reviewed_by_doctor == False
    ).order_by(PatientCase.created_at.desc()).all()

    # Open pool (unassigned + submitted + not reviewed)
    open_pool = db.query(PatientCase).filter(
        PatientCase.assigned_doctor_id == None,
        PatientCase.status == "submitted",
        PatientCase.reviewed_by_doctor == False
    ).order_by(PatientCase.created_at.desc()).all()

    # Closed cases (reviewed by me)
    closed_cases = db.query(PatientCase).filter(
        PatientCase.assigned_doctor_id == current_user.id,
        PatientCase.reviewed_by_doctor == True
    ).order_by(PatientCase.updated_at.desc()).all()

    return {"my_cases": my_cases, "open_pool": open_pool, "closed_cases": closed_cases}


@router.post("/cases/{case_id}/accept", response_model=CaseOut, dependencies=[Depends(role_required("doctor"))])
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
        raise HTTPException(status_code=400, detail="Case already assigned to another doctor")

    from datetime import datetime
    case.assigned_doctor_id = current_user.id
    case.assigned_at = datetime.utcnow()
    db.commit()
    db.refresh(case)

    # WebSocket notification to patient
    from app.core.websocket_manager import manager
    try:
        patient_user = db.query(User).filter(
            (User.id == case.user_id) |
            (User.username == case.patient_name) |
            (User.full_name == case.patient_name)
        ).first()

        if patient_user:
            await manager.send_personal_message({
                "type": "case_update",
                "message": f"Your case has been accepted by Dr. {current_user.full_name or current_user.username}"
            }, patient_user.id)
            logger.info(f"WebSocket notification sent to patient {patient_user.id}")
    except Exception as e:
        logger.warning(f"WebSocket notification failed (non-critical): {e}")

    return case


@router.get("/stats", dependencies=[Depends(role_required("doctor"))])
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get doctor statistics."""
    closed_count = db.query(PatientCase).filter(
        PatientCase.assigned_doctor_id == current_user.id,
        PatientCase.reviewed_by_doctor == True
    ).count()

    pending_count = db.query(PatientCase).filter(
        PatientCase.assigned_doctor_id == current_user.id,
        PatientCase.reviewed_by_doctor == False
    ).count()

    return {
        "total_cases_closed": closed_count,
        "total_cases_pending": pending_count
    }


@router.post("/review/{case_id}", response_model=CaseOut, dependencies=[Depends(role_required("doctor"))])
async def review_case(
    case_id: int,
    notes: str = Body(...),
    diagnosis: str = Body(None),
    severity_score: float = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit review notes and diagnosis for a case."""
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.assigned_doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this case")
    if case.reviewed_by_doctor:
        raise HTTPException(status_code=400, detail="Case already reviewed. Cannot submit again.")

    case.doctor_notes = notes
    if diagnosis:
        case.diagnosis = diagnosis
    if severity_score is not None:
        case.severity_score = severity_score

    # Determine final status
    if case.test_ordered and case.test_status == "pending":
        case.reviewed_by_doctor = False
        case.status = "waiting_lab"
    else:
        case.reviewed_by_doctor = True
        case.status = "completed"

    db.add(case)
    db.commit()
    db.refresh(case)

    # WebSocket notification
    from app.core.websocket_manager import manager
    try:
        patient_user = db.query(User).filter(
            (User.id == case.user_id) |
            (User.username == case.patient_name)
        ).first()

        if patient_user:
            msg = (
                f"Your case has been reviewed. Diagnosis: {case.diagnosis or 'See details'}"
                if case.reviewed_by_doctor
                else "Your case review is pending lab results"
            )
            await manager.send_personal_message({"type": "case_update", "message": msg}, patient_user.id)
    except Exception as e:
        logger.warning(f"WebSocket notification failed: {e}")

    return case


@router.post("/cases/{case_id}/order-test", response_model=CaseOut, dependencies=[Depends(role_required("doctor"))])
def order_test(
    case_id: int,
    test_type: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Order a diagnostic test for a patient case."""
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.assigned_doctor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this case")

    case.test_ordered = True
    case.ordered_test_type = test_type
    case.test_status = "recommended"
    db.commit()
    db.refresh(case)
    return case
