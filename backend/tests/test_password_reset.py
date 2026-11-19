"""Password reset flow tests."""

import hashlib

import pytest
from httpx import AsyncClient

from app.core import verify_password
from app.email.providers.mock import clear_mock_outbox, sent_messages
from app.models.user import User


@pytest.fixture(autouse=True)
def _clear_email_outbox():
    clear_mock_outbox()
    yield
    clear_mock_outbox()


@pytest.mark.asyncio
async def test_forgot_password_queues_email(client: AsyncClient, demo_user: User):
    res = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": demo_user.email},
    )
    assert res.status_code == 200
    assert len(sent_messages) == 1
    assert "reset-password?token=" in sent_messages[0].text_body


@pytest.mark.asyncio
async def test_reset_password_updates_hash(client: AsyncClient, db_session, demo_user: User):
    token = "reset-token-plaintext"
    from datetime import datetime, timedelta, timezone

    await db_session.users.update_one({"_id": demo_user.id}, {"$set": {"reset_token": hashlib.sha256(token.encode()).hexdigest(), "reset_token_expires": datetime.now(timezone.utc) + timedelta(minutes=30)}})

    res = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "NewPassword123!"},
    )
    assert res.status_code == 200

    updated = await db_session.users.find_one({"_id": demo_user.id})
    assert "reset_token" not in updated
    assert verify_password("NewPassword123!", updated["password_hash"])
