"""MongoDB documents used by the RBAC and audit layers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class Role(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    display_name: str
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Permission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str | None = None
    resource: str
    action: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserRole(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    role_id: str
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assigned_by: str | None = None


class RolePermission(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role_id: str
    permission_id: str
