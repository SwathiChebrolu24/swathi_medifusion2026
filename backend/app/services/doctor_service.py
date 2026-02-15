from sqlalchemy.orm import Session
from app.models.case import Case

def get_new_processed_cases(db: Session):
    return db.query(Case).filter(Case.status == "processed", Case.reviewed_by_doctor == False).order_by(Case.created_at.desc()).all()
