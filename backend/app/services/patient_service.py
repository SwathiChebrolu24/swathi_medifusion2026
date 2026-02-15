from sqlalchemy.orm import Session
from app.models.case import Case

def get_patient_cases(db: Session, patient_name: str):
    return db.query(Case).filter(Case.patient_name == patient_name).order_by(Case.created_at.desc()).all()
