"""
CivicLens — Authentication Integration Tests
"""

import pytest
from httpx import AsyncClient
from app.email.providers.mock import clear_mock_outbox, sent_messages


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    # 1. Request email OTP; no account exists yet
    clear_mock_outbox()
    reg_payload = {
        "email": "newcitizen@example.com",
        "password": "Password123!",
        "full_name": "Jane Citizen",
        "verification_method": "email",
    }
    otp_res = await client.post("/api/v1/auth/register/request-otp", json=reg_payload)
    assert otp_res.status_code == 200
    session = otp_res.json()["data"]
    code = sent_messages[-1].text_body.split("code is ", 1)[1].split(".", 1)[0]
    verify_res = await client.post("/api/v1/auth/register/verify-otp", json={"verification_session_id": session["verification_session_id"], "verification_token": session["verification_token"], "code": code})
    assert verify_res.status_code == 200
    reg_res = await client.post("/api/v1/auth/register", json={
        "verification_session_id": session["verification_session_id"],
        "verification_token": session["verification_token"],
    })
    assert reg_res.status_code == 200
    data = reg_res.json()
    assert data["success"] is True
    assert "access_token" in data["data"]
    assert data["data"]["user"]["email"] == "newcitizen@example.com"
    assert data["data"]["user"]["roles"] == ["citizen"]
    assert data["data"]["user"]["is_verified"] is True
    assert "refresh_token" not in data["data"]
    assert "refresh_token=" in reg_res.headers.get("set-cookie", "")

    upload_res = await client.post(
        "/api/v1/media/upload",
        files={"file": ("evidence.png", b"not an image", "image/png")},
        headers={"Authorization": f"Bearer {data['data']['access_token']}"},
    )
    assert upload_res.status_code in [400, 422]

    # 2. Login with registered credentials
    login_payload = {
        "email": "newcitizen@example.com",
        "password": "Password123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    login_data = login_res.json()
    token = login_data["data"]["access_token"]
    assert token is not None
    assert "refresh_token" not in login_data["data"]
    assert "refresh_token=" in login_res.headers.get("set-cookie", "")
    old_refresh_token = login_res.cookies.get("refresh_token")
    assert old_refresh_token

    refresh_res = await client.post("/api/v1/auth/refresh", json={})
    assert refresh_res.status_code == 200
    assert "refresh_token" not in refresh_res.json()["data"]
    assert refresh_res.json()["data"]["access_token"] != token

    replay_res = await client.post(
        "/api/v1/auth/refresh",
        json={},
        cookies={"refresh_token": old_refresh_token},
    )
    assert replay_res.status_code == 401

    # 3. Access protected /me profile endpoint
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["data"]["full_name"] == "Jane Citizen"


@pytest.mark.asyncio
async def test_registration_rejects_privileged_fields(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "privilege-attempt@example.com",
            "password": "Password123!",
            "full_name": "Privilege Attempt",
            "role": "admin",
            "department_id": "00000000-0000-0000-0000-000000000001",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, demo_user):
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": demo_user.email, "password": "WrongPassword!"},
    )
    assert login_res.status_code in [400, 401]
    assert login_res.json()["success"] is False
