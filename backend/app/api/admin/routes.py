from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.patient_case import PatientCase
from app.models.user import User
from app.core.role_checker import role_required
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", dependencies=[Depends(role_required("admin"))])
def get_admin_stats(db: Session = Depends(get_db)):
    """Get analytics for the admin dashboard."""

    # 1. Total Cases
    total_cases = db.query(PatientCase).count()

    # 2. Cases by Status
    status_counts = db.query(
        PatientCase.status, func.count(PatientCase.status)
    ).group_by(PatientCase.status).all()

    # 3. Disease Distribution — uses correct 'top_label' from Gemini AI
    cases_with_xray = db.query(PatientCase).filter(PatientCase.xray_result.isnot(None)).all()
    disease_counts = {"pneumonia": 0, "tuberculosis": 0, "covid": 0, "normal": 0, "other": 0}

    for case in cases_with_xray:
        if case.xray_result:
            # Support both old format (label) and new Gemini format (top_label)
            label = (
                case.xray_result.get("top_label") or
                case.xray_result.get("label") or ""
            ).lower()

            if "pneumonia" in label:
                disease_counts["pneumonia"] += 1
            elif "tuberculosis" in label or "tb" in label:
                disease_counts["tuberculosis"] += 1
            elif "covid" in label:
                disease_counts["covid"] += 1
            elif "normal" in label:
                disease_counts["normal"] += 1
            else:
                disease_counts["other"] += 1

    # 4. Average Severity
    avg_severity = db.query(func.avg(PatientCase.severity_score)).scalar() or 0.0

    # 5. Total Users by Role
    user_counts = db.query(
        User.role, func.count(User.role)
    ).group_by(User.role).all()

    logger.info(f"Admin stats fetched: {total_cases} total cases")

    return {
        "total_cases": total_cases,
        "status_breakdown": {s: c for s, c in status_counts},
        "disease_distribution": disease_counts,
        "average_severity": round(float(avg_severity), 2),
        "users_by_role": {r: c for r, c in user_counts}
    }
