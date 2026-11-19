import pytest

from app.core import create_access_token, hash_password
from app.core.mongo import model_to_doc
from app.models.user import User


@pytest.mark.asyncio
async def test_phone_otp_is_hashed_rate_limited_and_verifiable(client, db_session, monkeypatch):
    user = User(
        email="otp@example.com",
        full_name="OTP Citizen",
        phone="+919876543210",
        password_hash=hash_password("Password123!"),
        roles=["citizen"],
        is_active=True,
    )
    await db_session.users.insert_one(model_to_doc(user))
    monkeypatch.setattr("app.services.auth_service.secrets.randbelow", lambda _: 123456)

    async def deliver(phone: str, body: str):
        assert phone == "+919876543210"
        assert "123456" in body
        return "sent", None

    monkeypatch.setattr("app.services.auth_service.send_sms", deliver)
    headers = {"Authorization": f"Bearer {create_access_token(user.id, ['citizen'])}"}

    requested = await client.post("/api/v1/auth/phone/request-otp", json={}, headers=headers)
    assert requested.status_code == 200

    challenge = await db_session.otp_challenges.find_one({"user_id": user.id})
    assert challenge["code_hash"] != "123456"
    assert challenge["status"] == "pending"

    verified = await client.post(
        "/api/v1/auth/phone/verify-otp",
        json={"code": "123456"},
        headers=headers,
    )
    assert verified.status_code == 200
    stored = await db_session.users.find_one({"_id": user.id})
    assert stored["mobile_verified"] is True
