"""
Development-only provider.

Does not perform government identity verification and never marks users verified.
Use seeded or admin-assisted staging flows for verified test accounts.
"""

from __future__ import annotations

from typing import Any

from app.identity.base import IdentityProvider
from app.identity.types import ProviderCapabilities, SessionCompleteResult, SessionStartResult


class DevelopmentIdentityProvider(IdentityProvider):
    name = "development"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_citizen_registration=True,
            supports_verification_sessions=True,
            is_sandbox=True,
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
            status="development",
            message=(
                "Development mode: no government identity verification is performed. "
                "Configure a UIDAI-authorized provider before production."
            ),
            user_action={
                "type": "none",
                "note": "Complete identity verification is unavailable in development mode.",
            },
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
            status="development",
            message="Development mode cannot complete real identity verification.",
            verified=False,
            failure_code="DEVELOPMENT_MODE",
        )
