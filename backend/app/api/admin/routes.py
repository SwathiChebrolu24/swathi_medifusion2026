from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.patient_case import PatientCase
from app.models.user import User
from app.utils.security import require_role

router = APIRouter()

@router.get("/stats", dependencies=[Depends(require_role("admin"))])
def get_admin_stats(db: Session = Depends(get_db)):
    """
    Get analytics for the admin dashboard.
    """
    # 1. Total Cases
    total_cases = db.query(PatientCase).count()
    
    # 2. Cases by Status
    status_counts = db.query(
        PatientCase.status, func.count(PatientCase.status)
    ).group_by(PatientCase.status).all()
    
    # 3. Disease Distribution (from X-ray results)
    # This is a bit complex with JSON, so we'll do a simple approximation in Python for now
    # In production, use JSON operators in SQL
    cases_with_xray = db.query(PatientCase).filter(PatientCase.xray_result.isnot(None)).all()
    disease_counts = {"pneumonia": 0, "normal": 0, "other": 0}
    
    for case in cases_with_xray:
        if case.xray_result and "label" in case.xray_result:
            label = case.xray_result["label"].lower()
            if "pneumonia" in label:
                disease_counts["pneumonia"] += 1
            elif "normal" in label:
                disease_counts["normal"] += 1
            else:
                disease_counts["other"] += 1
                
    # 4. Average Severity
    avg_severity = db.query(func.avg(PatientCase.severity_score)).scalar() or 0.0
    
    return {
        "total_cases": total_cases,
        "status_breakdown": {s: c for s, c in status_counts},
        "disease_distribution": disease_counts,
        "average_severity": round(avg_severity, 2)
    }
