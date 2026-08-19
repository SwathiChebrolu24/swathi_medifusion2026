# app/schemas/user_schema.py
from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str                              # patient | doctor | lab
    license_code: Optional[str] = None    # Required for doctor/lab


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}  # Pydantic v2
