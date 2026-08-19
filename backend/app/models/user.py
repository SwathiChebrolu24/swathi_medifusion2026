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

    is_verified = Column(Boolean, default=False)

    is_doctor = Column(Boolean, default=False)
    is_lab = Column(Boolean, default=False)
