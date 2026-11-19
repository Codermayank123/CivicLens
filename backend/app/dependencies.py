"""
CivicLens — FastAPI Dependency Injections
Exposes database sessions, authentication, and role authorization dependencies.
"""

from app.database import get_db
from app.core.permissions import (
    get_current_user,
    require_roles,
    require_permission,
    check_resource_ownership,
)

__all__ = [
    "get_db",
    "get_current_user",
    "require_roles",
    "require_permission",
    "check_resource_ownership",
]
