from fastapi import Depends, HTTPException, status
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.core.security import get_current_user

def role_required(required_role: str):
    def checker(user = Depends(get_current_user)):
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Only {required_role}s are allowed."
            )
        return user
    return checker
