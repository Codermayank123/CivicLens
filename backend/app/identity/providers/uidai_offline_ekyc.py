"""
UIDAI Paperless Offline e-KYC verification.

Residents share offline e-KYC XML via mAadhaar with explicit consent. CivicLens
validates the XML signature when configured, compares minimal attributes, and
discards the document immediately. No Aadhaar number or OTP is stored.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from app.config import Settings
from app.identity.base import IdentityProvider
from app.identity.types import (
    OfflineEkycSubmission,
    ProviderCapabilities,
    SessionCompleteResult,
    SessionStartResult,
)


class UidaiOfflineEkycIdentityProvider(IdentityProvider):
    name = "uidai_offline_ekyc"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _cert_configured(self) -> bool:
        path = self._settings.UIDAI_OFFLINE_EKYC_CERT_PATH.strip()
        return bool(path and Path(path).is_file())

    def capabilities(self) -> ProviderCapabilities:
        ready = self._cert_configured()
        return ProviderCapabilities(
            supports_citizen_registration=False,
            supports_verification_sessions=ready,
            collects_aadhaar_on_server=False,
            collects_otp_on_server=False,
            is_sandbox=self._settings.IDENTITY_PROVIDER == "uidai_offline_ekyc"
            and self._settings.APP_ENV != "production",
            is_production_ready=False,
        )

    async def start_session(
        self,
        *,
        user_id: str,
        consent_version: str,
        session_id: str,
    ) -> SessionStartResult:
        if not self._cert_configured():
            return SessionStartResult(
                session_id=session_id,
                status="unavailable",
                message=(
                    "Offline e-KYC verification requires UIDAI_OFFLINE_EKYC_CERT_PATH "
                    "pointing to the UIDAI offline KYC public certificate."
                ),
            )

        return SessionStartResult(
            session_id=session_id,
            status="awaiting_user_action",
            message=(
                "Upload paperless offline e-KYC XML from mAadhaar. CivicLens validates "
                "the signature and does not retain the document."
            ),
            user_action={
                "type": "offline_ekyc_xml",
                "share_code_required": True,
                "documentation": "https://uidai.gov.in/en/ecosystem/authentication-devices-documents/developer-section.html",
            },
        )

    async def complete_session(
        self,
        *,
        user_id: str,
        session_id: str,
        payload: dict[str, Any],
    ) -> SessionCompleteResult:
        submission = OfflineEkycSubmission(
            share_code=payload.get("share_code"),
            encrypted_xml=payload.get("encrypted_xml"),
        )
        expected_name = payload.get("expected_full_name") or ""
        return await self.complete_offline_ekyc(
            user_id=user_id,
            session_id=session_id,
            submission=submission,
            expected_full_name=str(expected_name),
        )

    async def complete_offline_ekyc(
        self,
        *,
        user_id: str,
        session_id: str,
        submission: OfflineEkycSubmission,
        expected_full_name: str,
    ) -> SessionCompleteResult:
        if not self._cert_configured():
            return SessionCompleteResult(
                success=False,
                status="unavailable",
                message="Offline e-KYC certificate is not configured.",
                failure_code="CERT_NOT_CONFIGURED",
            )

        if not submission.encrypted_xml or not submission.share_code:
            return SessionCompleteResult(
                success=False,
                status="failed",
                message="Both encrypted_xml and share_code are required.",
                failure_code="MISSING_PAYLOAD",
            )

        if len(submission.encrypted_xml) > 512_000:
            return SessionCompleteResult(
                success=False,
                status="failed",
                message="Offline e-KYC payload exceeds allowed size.",
                failure_code="PAYLOAD_TOO_LARGE",
            )

        try:
            root = ET.fromstring(submission.encrypted_xml)
        except ET.ParseError:
            return SessionCompleteResult(
                success=False,
                status="failed",
                message="Invalid offline e-KYC XML.",
                failure_code="INVALID_XML",
            )

        name_value = self._extract_name(root)
        if not name_value:
            return SessionCompleteResult(
                success=False,
                status="failed",
                message="Could not read resident name from offline e-KYC XML.",
                failure_code="NAME_MISSING",
            )

        if not self._names_match(name_value, expected_full_name):
            return SessionCompleteResult(
                success=False,
                status="failed",
                message="Offline e-KYC name does not match the registered profile name.",
                failure_code="NAME_MISMATCH",
            )

        if not self._verify_xml_signature(root):
            return SessionCompleteResult(
                success=False,
                status="failed",
                message=(
                    "Offline e-KYC XML signature verification failed. "
                    "Ensure the XML is genuine and the UIDAI certificate is current."
                ),
                failure_code="SIGNATURE_INVALID",
            )

        return SessionCompleteResult(
            success=True,
            status="completed",
            message="Offline e-KYC verification succeeded.",
            verified=True,
        )

    def _extract_name(self, root: ET.Element) -> str | None:
        for elem in root.iter():
            tag = elem.tag.split("}")[-1].lower()
            if tag in {"name", "poiname", "residentname"} and elem.text:
                return elem.text.strip()
        return None

    def _names_match(self, ekyc_name: str, profile_name: str) -> bool:
        def normalize(value: str) -> str:
            return re.sub(r"[^a-z0-9]+", "", value.lower())

        ekyc_norm = normalize(ekyc_name)
        profile_norm = normalize(profile_name)
        if not ekyc_norm or not profile_norm:
            return False
        return ekyc_norm == profile_norm or ekyc_norm in profile_norm or profile_norm in ekyc_norm

    def _verify_xml_signature(self, root: ET.Element) -> bool:
        """
        Placeholder for UIDAI offline XML signature verification.

        Production deployments must verify the XML digital signature using the UIDAI
        offline KYC certificate and published algorithms. Returning False until
        wired to a compliant verifier prevents false positives.
        """
        _ = root
        return False
