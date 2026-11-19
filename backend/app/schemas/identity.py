"""Identity verification API schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IdentityStatusResponse(BaseModel):
    provider: str
    citizen_registration_enabled: bool
    supports_verification_sessions: bool
    collects_otp_on_server: bool
    collects_aadhaar_on_server: bool
    is_sandbox: bool
    is_production_ready: bool
    consent_version: str


class StartIdentitySessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_accepted: bool
    consent_version: str = Field(min_length=1, max_length=32)


class IdentitySessionResponse(BaseModel):
    session_id: str
    status: str
    message: str | None = None
    expires_at: str | None = None
    user_action: dict[str, Any] | None = None
    official_endpoints: dict[str, str] | None = None
    verified: bool | None = None
    provider: str | None = None
    completed_at: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None


class CompleteIdentitySessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signed_auth_response: str | None = Field(default=None, max_length=200_000)
    encrypted_xml: str | None = Field(default=None, max_length=512_000)
    share_code: str | None = Field(default=None, min_length=4, max_length=16)
