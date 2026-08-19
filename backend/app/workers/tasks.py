from celery import Celery
import os
from app.core.database import SessionLocal
from app.models.patient_case import PatientCase
from app.ai.predictor import analyze_image_bytes, analyze_symptoms
import logging

logger = logging.getLogger(__name__)

# Redis URL from environment — fallback to localhost for local dev
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "medifusion_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
)


def calculate_severity(xray_result, symptom_result) -> float:
    """
    Calculate severity score (0.0–10.0).
    Weighted: X-ray 60% + Symptoms 40%
    """
    xray_score = 0.0
    if xray_result:
        label = (xray_result.get("top_label") or xray_result.get("label") or "").lower()
        prob = float(xray_result.get("top_prob") or xray_result.get("prob") or 0)
        if "pneumonia" in label or "covid" in label or "tuberculosis" in label:
            xray_score = 5.0 + (prob * 5.0)
        elif "normal" in label:
            xray_score = prob * 2.0
        else:
            xray_score = 3.0 + (prob * 4.0)

    symptom_score = 0.0
    if symptom_result:
        label = (symptom_result.get("top_label") or symptom_result.get("label") or "").lower()
        prob = float(symptom_result.get("top_prob") or symptom_result.get("prob") or 0)
        if "pneumonia" in label or "covid" in label:
            symptom_score = 6.0 + (prob * 4.0)
        elif "normal" in label or "healthy" in label:
            symptom_score = prob * 2.0
        else:
            symptom_score = 3.0 + (prob * 4.0)

    # Weighted average
    if xray_result and symptom_result:
        score = (xray_score * 0.6) + (symptom_score * 0.4)
    elif xray_result:
        score = xray_score
    else:
        score = symptom_score

    return round(min(score, 10.0), 2)


@celery.task
def process_case_task(case_id: int):
    """Background task: run AI if not already done and recalculate severity."""
    db = SessionLocal()
    try:
        case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
        if not case:
            return None

        # Run X-ray AI if not already done
        if not case.xray_result and case.uploaded_file:
            if os.path.exists(case.uploaded_file):
                with open(case.uploaded_file, "rb") as f:
                    image_bytes = f.read()
                case.xray_result = analyze_image_bytes(image_bytes)
            else:
                logger.warning(f"File not found for case {case_id}: {case.uploaded_file}")

        # Run symptom AI if not already done
        if not case.symptom_result and case.symptoms:
            case.symptom_result = analyze_symptoms(case.symptoms)

        # Recalculate severity
        case.severity_score = calculate_severity(case.xray_result, case.symptom_result)
        case.status = "processed"
        db.commit()
        logger.info(f"Case {case_id} processed. Severity: {case.severity_score}")
        return case_id

    except Exception as e:
        logger.error(f"Error processing case {case_id}: {e}")
        db.rollback()
    finally:
        db.close()
