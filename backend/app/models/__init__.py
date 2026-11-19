"""CivicLens Models Package — Import all models for Alembic autogenerate."""

from app.models.user import User  # noqa: F401
from app.models.role import Role, Permission, UserRole, RolePermission  # noqa: F401
from app.models.department import Department  # noqa: F401
from app.models.department import ComplaintCategory  # noqa: F401
from app.models.complaint import (  # noqa: F401
    Complaint,
    ComplaintMedia,
    ComplaintAssignment,
    ComplaintStatusHistory,
    ComplaintComment,
    ComplaintDuplicate,
    ComplaintVerification,
    SyncEvent,
)
from app.models.notification import Notification  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.ai_prediction import AIPrediction  # noqa: F401
from app.models.identity import IdentityVerificationSession  # noqa: F401

__all__ = [
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "Department",
    "ComplaintCategory",
    "Complaint",
    "ComplaintMedia",
    "ComplaintAssignment",
    "ComplaintStatusHistory",
    "ComplaintComment",
    "ComplaintDuplicate",
    "ComplaintVerification",
    "SyncEvent",
    "Notification",
    "AuditLog",
    "AIPrediction",
    "IdentityVerificationSession",
]
