"""Email provider tests."""

import pytest

from app.email.base import EmailMessage
from app.email.providers.mock import MockEmailProvider, clear_mock_outbox, sent_messages
from app.config import Settings


@pytest.mark.asyncio
async def test_mock_email_provider_records_messages():
    clear_mock_outbox()
    provider = MockEmailProvider()
    await provider.send(
        EmailMessage(to="user@example.com", subject="Hello", text_body="Test body")
    )
    assert len(sent_messages) == 1
    assert sent_messages[0].to == "user@example.com"


def test_production_email_registry_rejects_mock():
    with pytest.raises(ValueError, match="EMAIL_PROVIDER must use a real delivery provider"):
        Settings(
            APP_ENV="production",
            DEBUG=False,
            JWT_SECRET_KEY="x" * 64,
            MEDIA_SIGNING_SECRET="y" * 64,
            S3_ACCESS_KEY="prod-key",
            S3_SECRET_KEY="prod-secret",
            AI_MOCK_MODE=False,
            EMAIL_PROVIDER="mock",
            BACKEND_CORS_ORIGINS="https://app.example.com",
            BACKEND_PUBLIC_URL="https://api.example.com",
        )
