"""Identity verification and staff provisioning tests."""

import pytest
from httpx import AsyncClient
from app.email.providers.mock import clear_mock_outbox, sent_messages

from app.config import Settings
from app.core import create_access_token
from app.identity.providers.uidai_offline_ekyc import UidaiOfflineEkycIdentityProvider
from app.identity.providers.uidai_sandbox import UidaiSandboxIdentityProvider
from app.core.mongo import model_to_doc
from app.models.department import Department
from app.models.user import User


@pytest.mark.asyncio
async def test_uidai_sandbox_does_not_trust_unverified_response():
    provider = UidaiSandboxIdentityProvider(
        Settings(
            UIDAI_AUA_CODE="test-aua",
            UIDAI_LICENSE_KEY="test-license",
        )
    )

    result = await provider.complete_session(
        user_id="test-user",
        session_id="test-session",
        payload={"signed_auth_response": "<unverified>response</unverified>"},
    )

    assert result.success is False
    assert result.verified is not True
    assert result.failure_code == "VERIFIER_NOT_IMPLEMENTED"


def test_offline_ekyc_does_not_advertise_unimplemented_verification(tmp_path):
    certificate = tmp_path / "uidai.pem"
    certificate.write_text("test certificate")
    provider = UidaiOfflineEkycIdentityProvider(
        Settings(UIDAI_OFFLINE_EKYC_CERT_PATH=str(certificate))
    )

    capabilities = provider.capabilities()

    assert capabilities.supports_citizen_registration is False
    assert capabilities.is_production_ready is False


@pytest.mark.asyncio
async def test_identity_status_development(client: AsyncClient):
    res = await client.get("/api/v1/identity/status")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["provider"] == "development"
    assert data["collects_otp_on_server"] is False
    assert data["citizen_registration_enabled"] is True


@pytest.mark.asyncio
async def test_identity_session_rejects_otp_payload(client: AsyncClient):
    clear_mock_outbox()
    request = await client.post(
        "/api/v1/auth/register/request-otp",
        json={
            "email": "idv-user@example.com",
            "password": "Password123!",
            "full_name": "IDV User",
            "verification_method": "email",
        },
    )
    session = request.json()["data"]
    code = sent_messages[-1].text_body.split("code is ", 1)[1].split(".", 1)[0]
    await client.post("/api/v1/auth/register/verify-otp", json={
        "verification_session_id": session["verification_session_id"],
        "verification_token": session["verification_token"],
        "code": code,
    })
    reg = await client.post("/api/v1/auth/register", json={
        "verification_session_id": session["verification_session_id"],
        "verification_token": session["verification_token"],
    })
    token = reg.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    start = await client.post(
        "/api/v1/identity/sessions",
        json={"consent_accepted": True, "consent_version": "2026-01"},
        headers=headers,
    )
    assert start.status_code == 422


@pytest.mark.asyncio
async def test_admin_can_create_staff_account(client: AsyncClient, db_session):
    dept = Department(name="Roads", code="ROADS", description="Roads dept")
    admin = User(
        email="staff-admin@example.com",
        full_name="Staff Admin",
        password_hash="x",
        roles=["admin"],
        is_active=True,
        is_verified=True,
    )
    await db_session.departments.insert_one(model_to_doc(dept))
    await db_session.users.insert_one(model_to_doc(admin))

    headers = {"Authorization": f"Bearer {create_access_token(str(admin.id), ['admin'])}"}
    res = await client.post(
        "/api/v1/users/staff",
        json={
            "email": "new-officer@example.com",
            "password": "Password123!",
            "full_name": "New Officer",
            "role": "officer",
            "department_id": str(dept.id),
        },
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["data"]["roles"] == ["officer"]


@pytest.mark.asyncio
async def test_citizen_cannot_create_staff(client: AsyncClient, demo_user: User):
    headers = {"Authorization": f"Bearer {create_access_token(str(demo_user.id), ['citizen'])}"}
    res = await client.post(
        "/api/v1/users/staff",
        json={
            "email": "blocked@example.com",
            "password": "Password123!",
            "full_name": "Blocked",
            "role": "admin",
        },
        headers=headers,
    )
    assert res.status_code == 403
