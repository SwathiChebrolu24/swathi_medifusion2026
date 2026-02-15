# app/api/ai/routes.py
from fastapi import APIRouter, UploadFile, File

router = APIRouter(prefix="/ai", tags=["AI"])

@router.post("/predict-from-image")
async def predict_image(file: UploadFile = File(...)):
    """
    Endpoint to receive an image file and return prediction.
    """
    contents = await file.read()

    # TODO: call your AI model here
    result = {"filename": file.filename, "prediction": "dummy_result"}

    return result
