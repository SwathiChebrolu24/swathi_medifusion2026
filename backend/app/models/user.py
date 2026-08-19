# app/models/user.py
from sqlalchemy import Column, String, Boolean, DateTime
from .base import Base, IdMixin
from datetime import datetime


class User(Base, IdMixin):
    __tablename__ = "users"

    username = Column(String, nullable=False, unique=True, index=True)
    password = Column(String, nullable=False)   # hashed password
    full_name = Column(String, nullable=True)
    role = Column(String, default="patient")
    specialty = Column(String, nullable=True)   # e.g. "pulmonologist"
    email = Column(String, nullable=True, unique=True, index=True)
    license_code = Column(String, nullable=True, unique=True)  # Unique license per doctor/lab

    # OTP & verification
    otp = Column(String, nullable=True)                        # Cleared after verify
    otp_created_at = Column(DateTime, nullable=True)           # For expiry check
    is_verified = Column(Boolean, default=False)               # True after OTP verify

    is_doctor = Column(Boolean, default=False)
    is_lab = Column(Boolean, default=False)
