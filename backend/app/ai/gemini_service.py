import os
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    logger.warning("⚠️ GEMINI_API_KEY not found in environment variables. AI features will fail.")

def get_gemini_model(model_name="gemini-1.5-flash"):
    """
    Get a Gemini model instance.
    """
    try:
        model = genai.GenerativeModel(model_name)
        return model
    except Exception as e:
        logger.error(f"❌ Error getting Gemini model: {e}")
        return None

def generate_text(prompt: str) -> str:
    """
    Generate text using Gemini Pro/Flash.
    """
    try:
        model = get_gemini_model("gemini-1.5-flash") # Use Flash for speed
        if not model: return "AI Error: Model not available"
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"❌ Gemini Text Generation Error: {e}")
        return "AI Error: Failed to generate response."

def analyze_image_with_text(image_bytes: bytes, prompt: str) -> str:
    """
    Analyze an image using Gemini Pro Vision.
    """
    try:
        model = get_gemini_model("gemini-1.5-flash")
        if not model: return "AI Error: Model not available"

        import PIL.Image
        import io
        image = PIL.Image.open(io.BytesIO(image_bytes))

        response = model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        logger.error(f"❌ Gemini Vision Error: {e}")
        return "AI Error: Failed to analyze image."
