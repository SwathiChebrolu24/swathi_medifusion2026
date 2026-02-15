from fastapi import HTTPException, Depends
from app.core.security import get_current_user
from app.models.user import User

def require_role(required_role: str):
    """
    Dependency to check if current user has the required role.
    Uses JWT token authentication via get_current_user.
    """
    def _check_role(current_user: User = Depends(get_current_user)):
        print(f"[AUTH] Checking role: required={required_role}, user={current_user.username}, role={current_user.role}")
        if current_user.role != required_role and current_user.role != "admin":
            print(f"[AUTH] FORBIDDEN: User {current_user.username} with role {current_user.role} tried to access {required_role} endpoint")
            raise HTTPException(
                status_code=403, 
                detail=f"Forbidden: {required_role} role required. You are logged in as {current_user.role}"
            )
        print(f"[AUTH] Access granted")
        return current_user
    return _check_role
