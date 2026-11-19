"""Short-lived registration verification sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class RegistrationVerification(BaseModel):
    id: str
    session_token_hash: str
    email: str
    full_name: str
    phone: str | None = None
    verification_method: Literal["email", "sms"]
    password_hash: str
    code_hash: str | None = None
    provider_verification_id: str | None = None
    attempts: int = 0
    request_count: int = 1
    status: Literal["pending", "verified", "consumed", "exhausted", "delivery_failed", "superseded"] = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    resend_available_at: datetime
    verified_at: datetime | None = None
