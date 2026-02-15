from pydantic import BaseModel
from typing import Dict, Any

class ReportCreate(BaseModel):
    title: str
    data: Dict[str, Any]
