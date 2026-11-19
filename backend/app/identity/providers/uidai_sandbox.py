"""
UIDAI sandbox integration (Auth / OTP / e-KYC 2.5).

Official sandbox documentation:
- https://uidai.gov.in/en/developer-section
- Auth 2.5: https://developer.uidai.gov.in/authserver/2.5
- OTP 2.5: https://developer.uidai.gov.in/uidotp/2.5
- e-KYC 2.5: https://developer.uidai.gov.in/uidkyc/kyc/2.5

CivicLens never collects Aadhaar OTPs on this server. OTP entry and PID encryption
must occur in a UIDAI-compliant client or ASA channel. This provider only records
consent, issues session metadata, and verifies signed authentication responses when
submitted after client-side completion.
"""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.identity.base import IdentityProvider
from app.identity.types import ProviderCapabilities, SessionCompleteResult, SessionStartResult


class UidaiSandboxIdentityProvider(IdentityProvider):
    name = "uidai_sandbox"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _configured(self) -> bool:
        return bool(self._settings.UIDAI_AUA_CODE.strip() and self._settings.UIDAI_LICENSE_KEY.strip())

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_citizen_registration=self._configured(),
            supports_verification_sessions=self._configured(),
            collects_aadhaar_on_server=False,
            collects_otp_on_server=False,
            is_sandbox=True,
            is_production_ready=False,
        )

    def _official_endpoints(self) -> dict[str, str]:
        return {
            "auth_2_5": self._settings.UIDAI_SANDBOX_AUTH_URL,
            "otp_2_5": self._settings.UIDAI_SANDBOX_OTP_URL,
            "ekyc_2_5": self._settings.UIDAI_SANDBOX_EKYC_URL,
        }

    async def start_session(
        self,
        *,
        user_id: str,
        consent_version: str,
        session_id: str,
    ) -> SessionStartResult:
        if not self._configured():
            return SessionStartResult(
                session_id=session_id,
                status="unavailable",
                message=(
                    "UIDAI sandbox is not configured. Set UIDAI_AUA_CODE and UIDAI_LICENSE_KEY "
                    "from your UIDAI developer registration."
                ),
            )

        return SessionStartResult(
            session_id=session_id,
            status="awaiting_user_action",
            message=(
                "Complete Aadhaar authentication using the UIDAI sandbox client flow. "
                "Do not send OTPs to CivicLens."
            ),
            user_action={
                "type": "uidai_client_auth",
                "otp_handling": "client_or_asa_only",
                "aua_code": self._settings.UIDAI_AUA_CODE,
            },
            official_endpoints=self._official_endpoints(),
        )

    async def complete_session(
        self,
        *,
        user_id: str,
        session_id: str,
        payload: dict[str, Any],
    ) -> SessionCompleteResult:
        if not self._configured():
            return SessionCompleteResult(
                success=False,
                status="unavailable",
                message="UIDAI sandbox credentials are not configured.",
                failure_code="UIDAI_NOT_CONFIGURED",
            )

        auth_response = payload.get("signed_auth_response")
        if not auth_response or not isinstance(auth_response, str):
            return SessionCompleteResult(
                success=False,
                status="failed",
                message=(
                    "Missing signed_auth_response from the UIDAI authentication flow. "
                    "CivicLens does not accept OTP values."
                ),
                failure_code="MISSING_AUTH_RESPONSE",
            )

        return SessionCompleteResult(
            success=False,
            status="pending_implementation",
            message=(
                "Received an authentication response, but server-side UIDAI "
                "signature and transaction validation are not implemented. "
                "The account remains unverified."
            ),
            failure_code="VERIFIER_NOT_IMPLEMENTED",
        )
