# app/utils/security.py
# Kept for backward compatibility — delegates to core.role_checker
from app.core.role_checker import role_required

__all__ = ["require_role", "role_required"]

# Alias for any code using the old name
require_role = role_required
