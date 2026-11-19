from __future__ import annotations

import httpx
import structlog

from app.email.base import EmailMessage

logger = structlog.get_logger()


class ResendEmailProvider:
    def __init__(self, *, api_key: str, from_address: str) -> None:
        self._api_key = api_key
        self._from = from_address

    async def send(self, message: EmailMessage) -> str | None:
        payload: dict[str, object] = {
            "from": self._from,
            "to": [message.to],
            "subject": message.subject,
            "text": message.text_body,
        }
        if message.html_body:
            payload["html"] = message.html_body
        if message.reply_to:
            payload["reply_to"] = [message.reply_to]

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if res.status_code >= 400:
            logger.error("email.resend.failed", status=res.status_code, body=res.text[:500])
            res.raise_for_status()
        logger.info("email.resend.sent", subject=message.subject)
        return str(res.json().get("id")) if isinstance(res.json(), dict) and res.json().get("id") else "resend-accepted"
