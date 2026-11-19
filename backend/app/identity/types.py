"""Shared types for identity verification providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IdentityProviderMode(str, Enum):
    DISABLED = "disabled"
    DEVELOPMENT = "development"
    UIDAI_SANDBOX = "uidai_sandbox"
    UIDAI_OFFLINE_EKYC = "uidai_offline_ekyc"


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_citizen_registration: bool
    supports_verification_sessions: bool
    collects_aadhaar_on_server: bool = False
    collects_otp_on_server: bool = False
    is_sandbox: bool = False
    is_production_ready: bool = False


@dataclass
class SessionStartResult:
    session_id: str
    status: str
    message: str
    user_action: dict[str, Any] = field(default_factory=dict)
    official_endpoints: dict[str, str] = field(default_factory=dict)


@dataclass
class SessionCompleteResult:
    success: bool
    status: str
    message: str
    verified: bool = False
    failure_code: str | None = None


@dataclass
class OfflineEkycSubmission:
    """Paperless offline e-KYC XML (transient — must not be logged or stored)."""

    share_code: str | None = None
    encrypted_xml: str | None = None
