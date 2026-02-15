# app/schemas/user_schema.py
from pydantic import BaseModel, EmailStr
from typing import Optional

# ------------------------------
# Base model for user creation
# ------------------------------
class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str  # doctor, lab, patient
    license_code: Optional[str] = None  # For doctor/lab verification
    email: Optional[EmailStr] = None  # Only for patient OTP

# ------------------------------
# Model returned after signup/login
# ------------------------------
class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
