"""Brevo transactional email provider."""

from __future__ import annotations

import asyncio
import base64
from typing import Any

import httpx
import structlog

from app.email.base import EmailMessage

logger = structlog.get_logger()


class BrevoEmailProvider:
    def __init__(self, *, api_key: str, sender_email: str, sender_name: str) -> None:
        self._api_key = api_key
        self._sender_email = sender_email
        self._sender_name = sender_name

    async def send(self, message: EmailMessage) -> str | None:
        payload: dict[str, Any] = {
            "sender": {"email": self._sender_email, "name": self._sender_name},
            "to": [{"email": message.to}],
            "subject": message.subject,
            "textContent": message.text_body,
            "htmlContent": message.html_body or message.text_body,
        }
        if message.reply_to:
            payload["replyTo"] = {"email": message.reply_to}
        if message.attachments:
            payload["attachment"] = [
                {
                    "name": attachment.filename,
                    "content": base64.b64encode(attachment.content).decode("ascii"),
                }
                for attachment in message.attachments
            ]

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        "https://api.brevo.com/v3/smtp/email",
                        headers={
                            "accept": "application/json",
                            "api-key": self._api_key,
                            "content-type": "application/json",
                        },
                        json=payload,
                    )
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < 2:
                        await asyncio.sleep(0.5 * (2**attempt))
                        continue
                if response.status_code >= 400:
                    logger.error("email.brevo.rejected", status=response.status_code)
                    response.raise_for_status()
                result = response.json()
                message_id = result.get("messageId") if isinstance(result, dict) else None
                logger.info("email.brevo.accepted", provider_message_id=bool(message_id))
                return str(message_id) if message_id else None
            except httpx.HTTPError as exc:
                if attempt < 2:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                logger.error("email.brevo.failed", error=type(exc).__name__)
                raise
        return None
