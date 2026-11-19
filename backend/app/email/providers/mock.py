from __future__ import annotations

from app.email.base import EmailMessage

# Captured messages for tests (cleared explicitly in test fixtures).
sent_messages: list[EmailMessage] = []


class MockEmailProvider:
    async def send(self, message: EmailMessage) -> str | None:
        sent_messages.append(message)
        return "mock-accepted"


def clear_mock_outbox() -> None:
    sent_messages.clear()
