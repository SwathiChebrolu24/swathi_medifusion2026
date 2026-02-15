from celery import Celery
import os
from app.core.database import SessionLocal
from app.models.patient_case import PatientCase
from app.ai.predictor import analyze_image_bytes, analyze_symptoms

celery = Celery(
    "medifusion_tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)

def calculate_severity(xray_result, symptom_result):
    """
    Calculate severity score (0.0 to 1.0).
    Weighted average: X-ray (60%) + Symptoms (40%)
    """
    xray_prob = 0.0
    if xray_result and "prob" in xray_result:
        # If pneumonia, use the prob. If normal, severity is low (1 - prob? No, prob is confidence of label)
        # If label is 'normal', severity is low.
        if xray_result.get("label") == "pneumonia":
            xray_prob = xray_result["prob"]
        else:
            xray_prob = 0.1 # Low severity for normal

    symptom_prob = 0.0
    if symptom_result and "prob" in symptom_result:
        # Similar logic
        label = symptom_result.get("label", "").lower()
        if "pneumonia" in label or "covid" in label:
            symptom_prob = symptom_result["prob"]
        else:
            symptom_prob = 0.1

    # Weighted score
    score = (xray_prob * 0.6) + (symptom_prob * 0.4)
    return round(score, 2)

@celery.task
def process_case_task(case_id: int):
    db = SessionLocal()
    try:
        case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
        if not case:
            return None

        # Run AI predictions if not already done
        if not case.xray_result and case.uploaded_file:
            # Use analyze_image_bytes which requires bytes
            if os.path.exists(case.uploaded_file):
                with open(case.uploaded_file, "rb") as f:
                    image_bytes = f.read()
                case.xray_result = analyze_image_bytes(image_bytes)
            else:
                print(f"File not found: {case.uploaded_file}")
            
        if not case.symptom_result and case.symptoms:
            case.symptom_result = analyze_symptoms(case.symptoms)

        # Calculate Severity
        case.severity_score = calculate_severity(case.xray_result, case.symptom_result)
        
        case.status = "processed"
        db.commit()
        return case_id
    except Exception as e:
        print(f"Error processing case {case_id}: {e}")
        db.rollback()
    finally:
        db.close()
