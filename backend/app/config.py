import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@db:5432/medifusion")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/app/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
