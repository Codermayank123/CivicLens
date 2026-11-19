"""SMS delivery adapters, including Message Central VerifyNow OTP."""

from __future__ import annotations

import asyncio
import hashlib
import re
from typing import Any

import httpx
import structlog

from app.config import get_settings

logger = structlog.get_logger()


def normalize_indian_phone(phone: str) -> tuple[str, str]:
    normalized = re.sub(r"[\s().-]", "", phone.strip())
    if normalized.startswith("00"):
        normalized = "+" + normalized[2:]
    if not re.fullmatch(r"\+91[6-9]\d{9}", normalized):
        raise ValueError("Message Central OTP requires an Indian +91 mobile number")
    return normalized, normalized[3:]


class MockSmsProvider:
    code_hashes: dict[str, str] = {}

    async def send_otp(self, phone: str, code: str | None = None) -> tuple[str, str | None, str | None]:
        normalized, _ = normalize_indian_phone(phone)
        if code is None:
            raise ValueError("Mock OTP requires a test code")
        self.code_hashes[normalized] = hashlib.sha256(code.encode()).hexdigest()
        return "sent", f"mock:{normalized}", None

    async def verify_otp(self, phone: str, verification_id: str, code: str) -> tuple[bool, str | None]:
        normalized, _ = normalize_indian_phone(phone)
        return self.code_hashes.get(normalized) == hashlib.sha256(code.encode()).hexdigest() and verification_id == f"mock:{normalized}", None


class MessageCentralProvider:
    def __init__(self, *, customer_id: str, auth_token: str, base_url: str) -> None:
        self._customer_id = customer_id
        self._auth_token = auth_token
        self._base_url = base_url.rstrip("/")

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.request(
                        method,
                        f"{self._base_url}{path}",
                        headers={"authToken": self._auth_token, "accept": "application/json"},
                        **kwargs,
                    )
                if (response.status_code == 429 or response.status_code >= 500) and attempt < 2:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                return response
            except httpx.HTTPError:
                if attempt == 2:
                    raise
                await asyncio.sleep(0.5 * (2**attempt))
        raise RuntimeError("Message Central request failed")

    async def send_otp(self, phone: str, code: str | None = None) -> tuple[str, str | None, str | None]:
        _, local_number = normalize_indian_phone(phone)
        # VerifyNow generates the OTP; code is accepted only for the mock-compatible interface.
        response = await self._request(
            "POST",
            "/verification/v3/send",
            params={
                "countryCode": "91",
                "flowType": "SMS",
                "mobileNumber": local_number,
                "customerId": self._customer_id,
                "otpLength": 6,
            },
        )
        if response.status_code >= 400:
            logger.warning("sms.message_central.send_rejected", status=response.status_code)
            return "failed", None, "Message Central rejected the OTP request"
        try:
            payload = response.json()
            data = payload.get("data") or {}
            verification_id = data.get("verificationId") or data.get("verficationId") or payload.get("verificationId")
        except ValueError:
            verification_id = None
        if not verification_id:
            return "failed", None, "Message Central did not return a verification id"
        return "sent", str(verification_id), None

    async def verify_otp(self, phone: str, verification_id: str, code: str) -> tuple[bool, str | None]:
        if not re.fullmatch(r"\d{4,8}", code):
            return False, "Invalid verification code"
        response = await self._request(
            "GET",
            "/verification/v3/validateOtp",
            params={"verificationId": verification_id, "code": code},
        )
        if response.status_code >= 400:
            return False, "Message Central rejected the verification code"
        try:
            payload = response.json()
            data = payload.get("data") or {}
            status = str(data.get("verificationStatus") or data.get("status") or payload.get("message") or "").upper()
            response_code = str(payload.get("responseCode") or data.get("responseCode") or response.status_code)
            return response_code in {"200", "SUCCESS"} and status in {"SUCCESS", "VERIFICATION_COMPLETED", "VERIFIED"}, None
        except ValueError:
            return False, "Message Central returned an invalid verification response"


def _provider() -> MessageCentralProvider | MockSmsProvider:
    settings = get_settings()
    if settings.SMS_PROVIDER.strip().lower() == "message_central":
        return MessageCentralProvider(
            customer_id=settings.MESSAGE_CENTRAL_CUSTOMER_ID,
            auth_token=settings.MESSAGE_CENTRAL_AUTH_TOKEN,
            base_url=settings.MESSAGE_CENTRAL_BASE_URL,
        )
    return MockSmsProvider()


async def send_otp(phone: str, code: str | None = None) -> tuple[str, str | None, str | None]:
    return await _provider().send_otp(phone, code)


async def verify_otp(phone: str, verification_id: str, code: str) -> tuple[bool, str | None]:
    return await _provider().verify_otp(phone, verification_id, code)


async def send_sms(to: str, body: str) -> tuple[str, str | None]:
    """Keep general SMS separate: VerifyNow is an OTP API, not notifications."""
    settings = get_settings()
    if settings.SMS_PROVIDER.strip().lower() == "mock":
        return "skipped", "SMS_PROVIDER is configured for test-only delivery"
    return "skipped", "Message Central VerifyNow is reserved for OTP delivery"
