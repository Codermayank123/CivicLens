"""
CivicLens — Department & Category MongoDB Models

Government departments and civic complaint categories.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class Department(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    code: str  # e.g., PWD, WSD, ELEC, SAN, TRF, PSF
    description: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    head_name: str | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ComplaintCategory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str  # pothole, garbage, broken_streetlight, etc.
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    department_id: str | None = None
    parent_id: str | None = None
    is_active: bool = True
    display_order: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
