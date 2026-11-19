from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage as StdEmailMessage

import structlog

from app.email.base import EmailMessage

logger = structlog.get_logger()


class SmtpEmailProvider:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        from_address: str,
        use_tls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from = from_address
        self._use_tls = use_tls

    async def send(self, message: EmailMessage) -> str | None:
        await asyncio.to_thread(self._send_sync, message)
        return "smtp-accepted"

    def _send_sync(self, message: EmailMessage) -> None:
        msg = StdEmailMessage()
        msg["Subject"] = message.subject
        msg["From"] = self._from
        msg["To"] = message.to
        if message.reply_to:
            msg["Reply-To"] = message.reply_to
        msg.set_content(message.text_body)
        if message.html_body:
            msg.add_alternative(message.html_body, subtype="html")

        with smtplib.SMTP(self._host, self._port, timeout=30) as smtp:
            if self._use_tls:
                smtp.starttls()
            if self._username:
                smtp.login(self._username, self._password)
            smtp.send_message(msg)
        logger.info("email.smtp.sent", subject=message.subject)
