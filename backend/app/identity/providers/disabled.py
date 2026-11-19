"""Provider used when identity verification is not configured."""

from __future__ import annotations

from typing import Any

from app.identity.base import IdentityProvider
from app.identity.types import ProviderCapabilities, SessionCompleteResult, SessionStartResult


class DisabledIdentityProvider(IdentityProvider):
    name = "disabled"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_citizen_registration=False,
            supports_verification_sessions=False,
            is_production_ready=False,
        )

    async def start_session(
        self,
        *,
        user_id: str,
        consent_version: str,
        session_id: str,
    ) -> SessionStartResult:
        return SessionStartResult(
            session_id=session_id,
            status="unavailable",
            message="Identity verification is not configured for this environment.",
        )

    async def complete_session(
        self,
        *,
        user_id: str,
        session_id: str,
        payload: dict[str, Any],
    ) -> SessionCompleteResult:
        return SessionCompleteResult(
            success=False,
            status="unavailable",
            message="Identity verification is not configured.",
            failure_code="PROVIDER_DISABLED",
        )
