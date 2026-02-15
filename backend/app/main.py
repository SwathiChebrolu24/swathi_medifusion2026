from dotenv import load_dotenv
import os
from pathlib import Path

# Load env vars
env_path = Path(__file__).parent.parent / '.env'
print(f"🔧 ENV DEBUG: Loading .env from {env_path}")
load_dotenv(dotenv_path=env_path, verbose=True)

print(f"🔧 ENV DEBUG: CWD={os.getcwd()}")
print(f"🔧 ENV DEBUG: DATABASE_URL={os.getenv('DATABASE_URL')}")
print(f"🔧 ENV DEBUG: DEV_MODE={os.getenv('DEV_MODE')}")

import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.base import Base
from app.core.database import engine, get_db
from app.api.auth.routes import router as auth_router
from app.api.patient.routes import router as patient_router
from app.api.doctor.routes import router as doctor_router
from app.api.admin.routes import router as admin_router
from app.api.websocket.routes import router as websocket_router
from app.api.chat.routes import router as chat_router
# from app.api.lab.routes import router as lab_router  # EXCLUDED FOR NOW

# ---------------------------------------------------
# AI Functions (Real Models)
# ---------------------------------------------------
from app.ai.predictor import (
    analyze_image_bytes,
    analyze_symptoms,
    analyze_text,
    summarize_report
)

# ---------------------------------------------------
# Logging
# ---------------------------------------------------
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ---------------------------------------------------
# FastAPI app
# ---------------------------------------------------
app = FastAPI(title="MediFusion Backend")

# ---------------------------------------------------
# Prometheus Instrumentation
# ---------------------------------------------------
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

# CORS Configuration - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom CORS middleware as fallback
@app.middleware("http")
async def add_cors_headers(request, call_next):
    origin = request.headers.get("origin")
    print(f"🔧 CORS DEBUG: Request from origin: {origin}")
    
    response = await call_next(request)
    
    # Force allow all origins for debugging
    if origin:
        print(f"🔧 CORS DEBUG: Adding headers for origin: {origin}")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response


# ---------------------------------------------------
# Database setup
# ---------------------------------------------------
DEV_MODE = os.getenv("DEV_MODE") == "1"

try:
    if DEV_MODE:
        logger.warning("⚠️ DEV_MODE is ON: resetting database...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database reset complete")
    else:
        Base.metadata.create_all(bind=engine)
except Exception as e:
    logger.error("❌ Database setup error: %s", e)

# ---------------------------------------------------
# Routers
# ---------------------------------------------------
app.include_router(auth_router)
app.include_router(patient_router, prefix="/patient", tags=["Patient"])
app.include_router(doctor_router, prefix="/doctor", tags=["Doctor"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(websocket_router, tags=["WebSocket"])
app.include_router(chat_router)
# app.include_router(lab_router, prefix="/lab", tags=["Lab"])  # EXCLUDED FOR NOW

# ---------------------------------------------------
# AI Test Models
# ---------------------------------------------------
class SymptomTest(BaseModel):
    symptoms: list[str]

@app.post("/test-ai-symptoms", tags=["AI Test"])
def test_ai_symptoms(data: SymptomTest):
    return {"input": data.symptoms, "prediction": "AI disabled"}
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version="1.0",
        description="MediFusion Backend API",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    if "/auth/me" in openapi_schema["paths"]:
        openapi_schema["paths"]["/auth/me"]["get"]["security"] = [
            {"OAuth2PasswordBearer": []}
        ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ---------------------------------------------------
# Actual AI Endpoints
# ---------------------------------------------------
@app.post("/predict-xray")
async def predict_xray(file: UploadFile):
    data = await file.read()
    return {"prediction": analyze_image_bytes(data)}

@app.post("/analyze-prescription")
async def analyze_prescription_endpoint(file: UploadFile):
    """
    Analyze uploaded prescription/medicine image.
    """
    from app.ai.predictor import analyze_prescription
    data = await file.read()
    return {"analysis": analyze_prescription(data)}

@app.post("/predict-symptoms")
async def predict_symptoms(symptoms: str = Form(...)):
    return {"prediction": analyze_symptoms(symptoms)}

@app.post("/predict-text")
async def predict_text(text: str = Form(...)):
    return {"prediction": analyze_text(text)}

@app.post("/summarize-report")
async def summarize_medical_report(
    report_text: str = Form(...),
    max_length: int = Form(150),
    min_length: int = Form(30)
):
    """
    Summarize a medical report using BART model.
    
    Args:
        report_text: Full medical report text
        max_length: Maximum summary length (default: 150)
        min_length: Minimum summary length (default: 30)
    
    Returns:
        Summary and metadata
    """
    try:
        result = summarize_report(report_text, max_length, min_length)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------
# Public Endpoints
# ---------------------------------------------------
@app.get("/doctors")
def get_doctors(db: Session = Depends(get_db)):
    """Fetch all registered doctors."""
    doctors = db.query(User).filter(User.role == "doctor").all()
    return [
        {
            "id": doc.id,
            "full_name": doc.full_name,
            "username": doc.username,
            "specialization": doc.specialty
        }
        for doc in doctors
    ]

if __name__ == "__main__":
    import uvicorn
    # Force reload trigger
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

