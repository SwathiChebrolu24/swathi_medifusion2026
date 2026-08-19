from fastapi import Depends, HTTPException, status
from app.core.security import get_current_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)


def role_required(required_role: str):
    """
    FastAPI dependency: ensures the current user has the required role.
    Admin users bypass all role checks.
    """
    def _check_role(current_user: User = Depends(get_current_user)):
        logger.debug(f"[AUTH] required={required_role} | user={current_user.username} | role={current_user.role}")
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. '{required_role}' role required. You are logged in as '{current_user.role}'."
            )
        return current_user
    return _check_role
