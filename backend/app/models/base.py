# app/models/base.py
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer

Base = declarative_base()

class IdMixin:
    id = Column(Integer, primary_key=True, index=True)
