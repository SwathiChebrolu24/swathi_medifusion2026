"""
Legacy AI Model loader module.
Kept for backward compatibility but models are no longer loaded locally.
"""

def load_biobert_model(): 
    return None

def load_pneumonia_model(): 
    return None

def load_summarization_model(): 
    return None

def load_text_model(): 
    return None

def load_model():
    return {"name": "gemini-cloud-ai"}
