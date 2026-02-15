import os
import uuid
from app.config import UPLOAD_DIR

def save_upload_file(upload_file) -> str:
    """
    Saves a FastAPI UploadFile to disk and returns saved filename (relative path).
    """
    ext = os.path.splitext(upload_file.filename)[1] or ""
    filename = f"{uuid.uuid4().hex}{ext}"
    out_path = os.path.join(UPLOAD_DIR, filename)
    with open(out_path, "wb") as f:
        f.write(upload_file.file.read())
    return out_path
