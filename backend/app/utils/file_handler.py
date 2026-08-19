import os
import uuid
from app.config import UPLOAD_DIR


def save_file_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Save raw bytes to the uploads directory.
    Returns the saved file path.
    """
    ext = os.path.splitext(filename)[1] if filename else ""
    unique_name = f"{uuid.uuid4().hex}{ext}"
    out_path = os.path.join(UPLOAD_DIR, unique_name)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(file_bytes)
    return out_path


def save_upload_file(upload_file) -> str:
    """
    Save a FastAPI UploadFile (sync) to disk.
    Returns saved file path.
    """
    ext = os.path.splitext(upload_file.filename)[1] if upload_file.filename else ""
    unique_name = f"{uuid.uuid4().hex}{ext}"
    out_path = os.path.join(UPLOAD_DIR, unique_name)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(upload_file.file.read())
    return out_path
