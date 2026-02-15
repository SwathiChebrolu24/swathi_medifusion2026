# app/api/predict/routes.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.patient_case import PatientCase
from app.ai.predictor import deterministic_image_predict, symptoms_to_prediction
from app.api.auth.routes import get_current_user
from app.models.user import User

router = APIRouter(prefix="/predict", tags=["Predict"])

# ---------------------------
# Predict from symptoms
# ---------------------------
class SymptomInput(BaseModel):
    symptoms: list[str] = Field(
        ..., example=["cough", "fever", "shortness of breath"]
    )

@router.post("/symptoms")
def predict_from_symptoms(
    data: SymptomInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prediction = symptoms_to_prediction(data.symptoms)
    
    # Save to DB
    case = PatientCase(
        patient_name=current_user.username,
        symptoms=",".join(data.symptoms),
        symptom_result=prediction,
        status="predicted"
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    
    return {"input": data.symptoms, "prediction": prediction, "case_id": case.id}

# ---------------------------
# Predict from image
# ---------------------------
import tempfile

@router.post("/image")
async def predict_from_image(
    file: UploadFile = File(..., description="Upload a chest X-ray image"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Save to temp file
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=file.filename)
        content = await file.read()
        temp.write(content)
        temp.close()

        # Pass file path to predictor
        prediction = deterministic_image_predict(temp.name)

        # Save to DB
        case = PatientCase(
            patient_name=current_user.username,
            uploaded_file=file.filename,
            xray_result=prediction,
            status="predicted"
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        return {"filename": file.filename, "prediction": prediction, "case_id": case.id}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------
# Get AI results from DB
# ---------------------------
@router.get("/case/{case_id}")
def get_case_prediction(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    case = db.query(PatientCase).filter(PatientCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Only the patient or a doctor can access the case
    if case.patient_name != current_user.username and current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Not authorized to view this case")
    
    return {
        "case_id": case.id,
        "xray_result": case.xray_result,
        "symptom_result": case.symptom_result,
        "status": case.status
    }
