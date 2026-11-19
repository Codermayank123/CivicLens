import pytest
from httpx import AsyncClient
from datetime import timedelta

from app.email.providers.mock import clear_mock_outbox, sent_messages
from app.core.mongo import utc_now
from app.exceptions import TokenInvalidError
from app.schemas.auth import VerifyRegistrationOtpRequest
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_email_registration_requires_verified_single_use_session(client: AsyncClient, db_session, monkeypatch):
    clear_mock_outbox()
    monkeypatch.setattr("app.services.auth_service.secrets.randbelow", lambda _: 123456)
    details = {
        "email": "otp-citizen@example.com",
        "password": "Password123!",
        "full_name": "OTP Citizen",
        "verification_method": "email",
    }
    requested = await client.post("/api/v1/auth/register/request-otp", json=details)
    assert requested.status_code == 200
    assert await db_session.users.count_documents({}) == 0
    data = requested.json()["data"]
    assert sent_messages[-1].text_body.find("123456") >= 0
    stored = await db_session.registration_verifications.find_one({"_id": data["verification_session_id"]})
    assert stored["code_hash"] != "123456"
    assert stored["status"] == "pending"

    invalid = await client.post(
        "/api/v1/auth/register/verify-otp",
            json={"verification_session_id": data["verification_session_id"], "verification_token": data["verification_token"], "code": "000000"},
    )
    assert invalid.status_code == 401

    verified = await client.post(
        "/api/v1/auth/register/verify-otp",
        json={"verification_session_id": data["verification_session_id"], "verification_token": data["verification_token"], "code": "123456"},
    )
    assert verified.status_code == 200
    created = await client.post("/api/v1/auth/register", json={
        "verification_session_id": data["verification_session_id"],
        "verification_token": data["verification_token"],
    })
    assert created.status_code == 200
    user = await db_session.users.find_one({"email": details["email"]})
    assert user["is_verified"] is True
    assert user["email_verified"] is True
    assert user["identity_provider"] == "otp_email"

    replay = await client.post("/api/v1/auth/register", json={
        "verification_session_id": data["verification_session_id"],
        "verification_token": data["verification_token"],
    })
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_sms_registration_uses_indian_number_and_mock_provider(client: AsyncClient, db_session, monkeypatch):
    monkeypatch.setattr("app.services.auth_service.secrets.randbelow", lambda _: 654321)
    requested = await client.post("/api/v1/auth/register/request-otp", json={
        "email": "sms-citizen@example.com",
        "password": "Password123!",
        "full_name": "SMS Citizen",
        "phone": "+919876543210",
        "verification_method": "sms",
    })
    assert requested.status_code == 200
    data = requested.json()["data"]
    verified = await client.post("/api/v1/auth/register/verify-otp", json={"verification_session_id": data["verification_session_id"], "verification_token": data["verification_token"], "code": "654321"})
    assert verified.status_code == 200
    created = await client.post("/api/v1/auth/register", json={
        "verification_session_id": data["verification_session_id"],
        "verification_token": data["verification_token"],
    })
    assert created.status_code == 200
    user = await db_session.users.find_one({"email": "sms-citizen@example.com"})
    assert user["mobile_verified"] is True
    assert user["email_verified"] is False


@pytest.mark.asyncio
async def test_registration_otp_cooldown_expiry_and_attempt_limit(client: AsyncClient, db_session, monkeypatch):
    monkeypatch.setattr("app.services.auth_service.secrets.randbelow", lambda _: 111111)
    details = {
        "email": "limits@example.com",
        "password": "Password123!",
        "full_name": "Limits Citizen",
        "verification_method": "email",
    }
    requested = await client.post("/api/v1/auth/register/request-otp", json=details)
    assert requested.status_code == 200
    session = requested.json()["data"]
    cooldown = await client.post("/api/v1/auth/register/request-otp", json=details)
    assert cooldown.status_code == 429

    await db_session.registration_verifications.update_one(
        {"_id": session["verification_session_id"]},
        {"$set": {"expires_at": utc_now() - timedelta(seconds=1)}},
    )
    expired = await client.post("/api/v1/auth/register/verify-otp", json={
        "verification_session_id": session["verification_session_id"],
        "verification_token": session["verification_token"],
        "code": "111111",
    })
    assert expired.status_code == 401

    limited = await client.post("/api/v1/auth/register/request-otp", json={**details, "email": "attempts@example.com"})
    assert limited.status_code == 200
    limited_session = limited.json()["data"]
    verify_payload = VerifyRegistrationOtpRequest(
        verification_session_id=limited_session["verification_session_id"],
        verification_token=limited_session["verification_token"],
        code="000000",
    )
    service = AuthService(db_session)
    for _ in range(5):
        with pytest.raises(TokenInvalidError):
            await service.verify_registration_otp(verify_payload)
    exhausted = await db_session.registration_verifications.find_one({"_id": limited_session["verification_session_id"]})
    assert exhausted["status"] == "exhausted"
    assert exhausted["attempts"] == 5
    with pytest.raises(TokenInvalidError):
        await service.verify_registration_otp(verify_payload)
