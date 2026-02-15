"""
AI Prediction functions for MediFusion backend.
Uses Google Gemini API for fast, accurate medical analysis.
"""
from typing import List, Union
import json
import logging
from app.ai.gemini_service import generate_text, analyze_image_with_text

logger = logging.getLogger(__name__)

# --------------------------
# Symptom Analysis
# --------------------------
def analyze_symptoms(symptoms_text: Union[str, List[str]]) -> dict:
    """
    Analyze symptoms using Gemini to predict potential conditions.
    """
    if isinstance(symptoms_text, list):
        text = " ".join(symptoms_text)
    else:
        text = symptoms_text or ""

    if not text.strip():
        return {"label": "unknown", "prob": 0.0, "predictions": []}

    prompt = f"""
    Act as a medical AI assistant. Analyze the following symptoms and provide a JSON response.
    Symptoms: "{text}"

    Task:
    1. Identify the top 3 potential medical conditions based on these symptoms.
    2. Provide a confidence score (0.0 to 1.0) for each.
    3. Provide a brief explanation (notes) for the top condition.
    4. Flag if it seems urgent (high/medium/low).

    Output JSON Format:
    {{
        "predictions": [
            {{"disease": "Condition Name", "confidence": 0.95}},
            {{"disease": "Condition Name", "confidence": 0.40}}
        ],
        "top_label": "Top Condition Name",
        "top_prob": 0.95,
        "notes": "Brief explanation...",
        "urgency": "high/medium/low"
    }}
    Return ONLY JSON.
    """

    try:
        response_text = generate_text(prompt)
        # Clean up code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()
            
        data = json.loads(response_text)
        return data
    except Exception as e:
        logger.error(f"Symptom Analysis Failed: {e}")
        return {
            "predictions": [{"disease": "Analysis Failed", "confidence": 0.0}],
            "top_label": "Error",
            "top_prob": 0.0,
            "notes": "Could not analyze symptoms at this time.",
            "urgency": "unknown"
        }

# --------------------------
# X-ray Analysis
# --------------------------
def analyze_image_bytes(image_bytes: bytes) -> dict:
    """
    Analyze chest X-ray image using Gemini Vision.
    """
    prompt = """
    Analyze this medical image (Chest X-Ray) as an expert radiologist.
    
    Task:
    1. Detect if there are signs of Pneumonia, Tuberculosis, COVID-19, or other lung pathologies.
    2. If the lungs appear normal, state "Normal".
    3. Provide a confidence score.

    Output JSON Format:
    {
        "predictions": [
            {"disease": "Pneumonia", "confidence": 0.88},
            {"disease": "Normal", "confidence": 0.12}
        ],
        "top_label": "Pneumonia",
        "top_prob": 0.88,
        "notes": "Key observation: Opacity observed in lower right lobe..."
    }
    Return ONLY JSON.
    """

    try:
        response_text = analyze_image_with_text(image_bytes, prompt)
         # Clean up code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()
            
        data = json.loads(response_text)
        return data
    except Exception as e:
        logger.error(f"Image Analysis Failed: {e}")
        return {
            "predictions": [{"disease": "Analysis Failed", "confidence": 0.0}],
            "top_label": "Error",
            "top_prob": 0.0,
            "notes": "Could not analyze image."
        }

# --------------------------
# Prescription Analysis
# --------------------------
def analyze_prescription(image_bytes: bytes) -> dict:
    """
    Analyze prescription/medicine image using Gemini Vision.
    """
    prompt = """
    Analyze this image of a medicine or doctor's prescription.
    
    Task:
    1. Identify the medicine names or prescribed drugs.
    2. Explain what each medicine is used for (Usage).
    3. List common side effects.
    4. Provide simple dosage instructions if visible (otherwise state "As prescribed by doctor").

    Output JSON Format:
    {
        "medicines": [
            {
                "name": "Amoxicillin",
                "usage": "Antibiotic for bacterial infections",
                "side_effects": "Nausea, rash, diarrhea",
                "dosage": "500mg, 3 times a day (if visible)"
            }
        ],
        "notes": "Consult your doctor before changing any dosage."
    }
    Return ONLY JSON.
    """

    try:
        response_text = analyze_image_with_text(image_bytes, prompt)
         # Clean up code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()
            
        data = json.loads(response_text)
        return data
    except Exception as e:
        logger.error(f"Prescription Analysis Failed: {e}")
        return {
            "medicines": [],
            "notes": "Could not analyze prescription. Please ensure image is clear.",
            "error": str(e)
        }

# --------------------------
# Summarization
# --------------------------
def summarize_report(report_text: str, max_length: int = 150, min_length: int = 30) -> dict:
    """
    Summarize medical report using Gemini.
    """
    prompt = f"""
    Summarize the following medical report content into a concise summary (approx {max_length} chars).
    Retain key medical findings and diagnosis.

    Report: "{report_text[:2000]}"
    """
    
    try:
        summary = generate_text(prompt)
        return {
            "summary": summary,
            "original_length": len(report_text),
            "summary_length": len(summary),
            "model": "gemini-1.5-flash"
        }
    except Exception as e:
        return {"summary": "Summarization failed.", "error": str(e)}

def analyze_text(text: str) -> dict:
    return {"label": "processed", "score": 1.0}

def analyze_symptom_severity(symptoms_text: str) -> dict:
    # Use the same logic as analyze_symptoms but focus on urgency
    data = analyze_symptoms(symptoms_text)
    return {
        "urgency": data.get("urgency", "low"),
        "confidence": data.get("top_prob", 0.5),
        "reason": data.get("notes", "")
    }

def summarize_case_history(case_data: dict) -> str:
    """
    Summarize a patient case using Gemini.
    """
    prompt = f"""
    Act as a medical assistant. Summarize the following patient case into a concise paragraph for a doctor's review.
    
    Patient Case Data:
    {json.dumps(case_data, indent=2)}
    
    Focus on:
    - Patient Name and Symptoms
    - Key AI Findings (X-Ray/Symptom analysis)
    - Calculated Severity Score
    """
    
    try:
        summary = generate_text(prompt)
        return summary
    except Exception as e:
        logger.error(f"Case Summarization Failed: {e}")
        return "Could not generate summary."

