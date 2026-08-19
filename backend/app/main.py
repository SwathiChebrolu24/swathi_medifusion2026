from dotenv import load_dotenv
import os
from pathlib import Path

# Load env vars
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, verbose=True)

import logging
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.base import Base
from app.core.database import engine, get_db
from app.core.schema_migrations import migrate_schema
from app.api.auth.routes import router as auth_router
from app.api.patient.routes import router as patient_router
from app.api.doctor.routes import router as doctor_router
from app.api.admin.routes import router as admin_router
from app.api.websocket.routes import router as websocket_router
from app.api.chat.routes import router as chat_router

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
logging.basicConfig(level=logging.INFO)
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

# ---------------------------------------------------
# CORS — single clean middleware
# Allows both Vercel frontend and localhost dev
# ---------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5500",
    "http://localhost:5173",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    # Vercel frontend
    "https://swathi-medifusion2026.vercel.app",
    "https://medifusion2026.vercel.app",
    # Add any other frontend URLs here
]

# Allow extra origins from env (comma-separated)
extra_origins = os.getenv("ALLOWED_ORIGINS", "")
if extra_origins:
    ALLOWED_ORIGINS.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------
# Database setup
# ---------------------------------------------------
DEV_MODE = os.getenv("DEV_MODE", "false").lower() in ("1", "true", "yes")

try:
    if DEV_MODE:
        logger.warning("⚠️  DEV_MODE is ON: resetting database...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database reset complete")
    else:
        Base.metadata.create_all(bind=engine)
        migrate_schema()
        logger.info("✅ Database tables ensured")
except Exception as e:
    logger.error("❌ Database setup error: %s", e)
    raise

# ---------------------------------------------------
# Routers
# ---------------------------------------------------
app.include_router(auth_router)
app.include_router(patient_router, prefix="/patient", tags=["Patient"])
app.include_router(doctor_router, prefix="/doctor", tags=["Doctor"])
app.include_router(admin_router, prefix="/admin", tags=["Admin"])
app.include_router(websocket_router, tags=["WebSocket"])
app.include_router(chat_router)

# ---------------------------------------------------
# OpenAPI / Swagger config
# ---------------------------------------------------
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
# AI Endpoints
# ---------------------------------------------------
class SymptomTest(BaseModel):
    symptoms: list[str]

@app.post("/test-ai-symptoms", tags=["AI Test"])
def test_ai_symptoms(data: SymptomTest):
    return {"input": data.symptoms, "prediction": "AI disabled"}

@app.post("/predict-xray")
async def predict_xray(file: UploadFile):
    data = await file.read()
    return {"prediction": analyze_image_bytes(data)}

@app.post("/analyze-prescription")
async def analyze_prescription_endpoint(file: UploadFile):
    """Analyze uploaded prescription/medicine image."""
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
    """Summarize a medical report using Gemini."""
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

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "MediFusion API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
