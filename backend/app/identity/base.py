"""Identity verification provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.identity.types import (
    OfflineEkycSubmission,
    ProviderCapabilities,
    SessionCompleteResult,
    SessionStartResult,
)


class IdentityProvider(ABC):
    name: str

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        raise NotImplementedError

    @abstractmethod
    async def start_session(
        self,
        *,
        user_id: str,
        consent_version: str,
        session_id: str,
    ) -> SessionStartResult:
        raise NotImplementedError

    @abstractmethod
    async def complete_session(
        self,
        *,
        user_id: str,
        session_id: str,
        payload: dict[str, Any],
    ) -> SessionCompleteResult:
        raise NotImplementedError

    async def complete_offline_ekyc(
        self,
        *,
        user_id: str,
        session_id: str,
        submission: OfflineEkycSubmission,
        expected_full_name: str,
    ) -> SessionCompleteResult:
        raise NotImplementedError

    async def handle_provider_callback(
        self,
        *,
        session_id: str,
        payload: dict[str, Any],
    ) -> SessionCompleteResult:
        return SessionCompleteResult(
            success=False,
            status="unsupported",
            message="This provider does not accept server callbacks",
            verified=False,
            failure_code="CALLBACK_UNSUPPORTED",
        )
