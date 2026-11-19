from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmailAttachment:
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text_body: str
    html_body: str | None = None
    reply_to: str | None = None
    attachments: tuple[EmailAttachment, ...] = ()


class EmailProvider(Protocol):
    async def send(self, message: EmailMessage) -> str | None: ...
