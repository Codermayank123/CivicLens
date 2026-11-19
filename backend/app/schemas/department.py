"""
CivicLens — Department & Category Schemas
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class DepartmentResponse(BaseModel):
    id: str
    name: str
    code: str
    description: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    head_user_id: str | None = None
    is_active: bool = True
    member_count: int = 0
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=50)
    description: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    department_id: str | None = None
    department_name: str | None = None
    parent_id: str | None = None
    is_active: bool = True
    display_order: int = 0

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=100)
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    department_id: str | None = None
    parent_id: str | None = None
    display_order: int = 0
