from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.ai.gemini_service import generate_text
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["AI Chatbot"])

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None

class ChatResponse(BaseModel):
    response: str

@router.post("/", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest, current_user: User = Depends(get_current_user)):
    """
    Chat with the AI Health Assistant.
    """
    try:
        user_context = f"User: {current_user.full_name} ({current_user.role})."
        if request.context:
            user_context += f" Context: {request.context}"

        prompt = f"""
        Act as a helpful, empathetic, and professional medical AI assistant named 'MediFusion AI'.
        {user_context}

        User Question: "{request.message}"

        Guidelines:
        1. Provide clear, accurate health information.
        2. Do NOT provide definitive medical diagnoses. Always advise consulting a doctor for serious issues.
        3. Be concise but thorough.
        4. If the user asks about app features, guide them.
        """

        response = generate_text(prompt)
        return {"response": response}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
