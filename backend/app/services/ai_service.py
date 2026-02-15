from app.ai.predictor import deterministic_image_predict, symptoms_to_prediction

def run_ai_on_image(path: str):
    return deterministic_image_predict(path)

def run_ai_on_symptoms(text: str):
    return symptoms_to_prediction(text)
