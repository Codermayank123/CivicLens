"""
CivicLens — Identity verification sessions (minimal retention).

Stores session state and audit-friendly metadata only. Never persist full Aadhaar
numbers, OTPs, or raw identity documents.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class IdentitySessionStatus(str, enum.Enum):
    PENDING = "pending"
    AWAITING_USER_ACTION = "awaiting_user_action"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class IdentityVerificationSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    provider: str
    status: IdentitySessionStatus = IdentitySessionStatus.PENDING
    consent_version: str
    consented_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    completed_at: datetime | None = None
    provider_reference: str | None = None
    outcome_fingerprint: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    client_metadata: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
