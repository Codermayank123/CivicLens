"""
CivicLens — Complaints Workflow Integration Tests
"""

import pytest
from httpx import AsyncClient

from app.core import create_access_token, hash_password
from app.core.mongo import model_to_doc
from app.exceptions import AccountNotVerifiedError
from app.models.complaint import ComplaintStatus
from app.models.user import User
from app.services.complaint_service import ComplaintService
from app.schemas.complaint import ComplaintCreate


async def _create_seed_complaint(db_session, demo_user, demo_category) -> str:
    service = ComplaintService(db_session)
    complaint = await service.create(
        demo_user,
        ComplaintCreate(
            title="Seeded complaint",
            description="Seeded description.",
            category_id=str(demo_category.id),
            priority="low",
            latitude=28.6139,
            longitude=77.209,
            address="Seed Street",
        ),
    )
    return complaint.id


@pytest.mark.asyncio
async def test_create_and_fetch_complaint(
    client: AsyncClient,
    user_token: str,
    demo_category,
    db_session,
):
    headers = {"Authorization": f"Bearer {user_token}"}

    anonymous_duplicate_check = await client.post(
        "/api/v1/complaints/duplicates/check",
        params={
            "title": "Pothole on Ring Road",
            "description": "A large pothole is damaging vehicles on the road.",
            "category_id": str(demo_category.id),
        },
    )
    assert anonymous_duplicate_check.status_code == 401

    # 1. Create Complaint
    payload = {
        "title": "Severe pothole near Ring Road overpass",
        "description": "Deep asphalt crater causing traffic slowdown and damaging vehicles.",
        "category_id": str(demo_category.id),
        "priority": "high",
        "latitude": 28.6139,
        "longitude": 77.209,
        "address": "Ring Road Sector 4",
    }
    create_res = await client.post("/api/v1/complaints", json=payload, headers=headers)
    assert create_res.status_code == 200
    res_data = create_res.json()
    assert res_data["success"] is True
    complaint = res_data["data"]
    complaint_id = complaint["id"]
    public_id = complaint["public_id"]

    assert complaint["title"] == payload["title"]
    assert complaint["status"] == "submitted"
    assert complaint["ai_category"] is not None

    status_res = await client.patch(
        f"/api/v1/complaints/{complaint_id}/status",
        json={"status": "under_review"},
        headers=headers,
    )
    assert status_res.status_code == 403

    internal_comment_res = await client.post(
        f"/api/v1/complaints/{complaint_id}/comments",
        json={"comment": "private note", "is_internal": True},
        headers=headers,
    )
    assert internal_comment_res.status_code == 403

    # 2. Fetch by Public ID
    get_res = await client.get(
        f"/api/v1/complaints/{public_id}",
        headers=headers,
    )
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == complaint_id

    # 3. Add Discussion Comment
    comment_payload = {"comment": "Work crew reported on site.", "is_internal": False}
    comment_res = await client.post(
        f"/api/v1/complaints/{complaint_id}/comments",
        json=comment_payload,
        headers=headers,
    )
    assert comment_res.status_code == 200
    assert comment_res.json()["data"]["comment"] == "Work crew reported on site."

    # 4. Verify Resolution
    verify_payload = {
        "action": "approved",
        "feedback": "Pothole completely repaired and leveled smoothly.",
        "rating": 5,
    }
    early_verify_res = await client.post(
        f"/api/v1/complaints/{complaint_id}/verify",
        json=verify_payload,
        headers=headers,
    )
    assert early_verify_res.status_code == 422

    await db_session.complaints.update_one({"_id": complaint_id}, {"$set": {"status": ComplaintStatus.RESOLVED.value}})

    verify_res = await client.post(
        f"/api/v1/complaints/{complaint_id}/verify",
        json=verify_payload,
        headers=headers,
    )
    assert verify_res.status_code == 200


@pytest.mark.asyncio
async def test_cannot_comment_on_unreadable_complaint(
    client: AsyncClient,
    db_session,
    demo_user,
    demo_category,
):
    """Object-level authorization must gate the comment endpoint, not just roles."""
    seed_headers = {"Authorization": f"Bearer {create_access_token(demo_user.id, ['citizen'])}"}
    complaint_id = await _create_seed_complaint(db_session, demo_user, demo_category)

    stranger = User(
        email="stranger@example.com",
        full_name="Stranger",
        password_hash=hash_password("Password123!"),
        roles=["citizen"],
        is_active=True,
        is_verified=True,
    )
    await db_session.users.insert_one(model_to_doc(stranger))
    stranger_headers = {"Authorization": f"Bearer {create_access_token(stranger.id, ['citizen'])}"}

    response = await client.post(
        f"/api/v1/complaints/{complaint_id}/comments",
        json={"comment": "should not be visible", "is_internal": False},
        headers=stranger_headers,
    )
    assert response.status_code == 403

    comments = await db_session.complaint_comments.find({"complaint_id": complaint_id}).to_list(length=10)
    assert comments == []


@pytest.mark.asyncio
async def test_owner_can_comment_and_staff_can_post_internal_note(
    client: AsyncClient,
    db_session,
    demo_user,
    demo_category,
):
    complaint_id = await _create_seed_complaint(db_session, demo_user, demo_category)
    owner_headers = {"Authorization": f"Bearer {create_access_token(demo_user.id, ['citizen'])}"}

    public = await client.post(
        f"/api/v1/complaints/{complaint_id}/comments",
        json={"comment": "Owner follow-up.", "is_internal": False},
        headers=owner_headers,
    )
    assert public.status_code == 200

    officer = User(
        email="officer@example.com",
        full_name="Officer",
        password_hash=hash_password("Password123!"),
        roles=["officer"],
        is_active=True,
        is_verified=True,
        department_id=demo_category.department_id,
    )
    await db_session.users.insert_one(model_to_doc(officer))
    officer_headers = {"Authorization": f"Bearer {create_access_token(officer.id, ['officer'])}"}

    internal = await client.post(
        f"/api/v1/complaints/{complaint_id}/comments",
        json={"comment": "Internal triage note.", "is_internal": True},
        headers=officer_headers,
    )
    assert internal.status_code == 200
    assert internal.json()["data"]["comment"] == "Internal triage note."


@pytest.mark.asyncio
async def test_unverified_user_cannot_submit_complaint(db_session, demo_category):
    user = User(
        email="unverified@example.com",
        full_name="Unverified Citizen",
        password_hash=hash_password("Password123!"),
        roles=["citizen"],
        is_active=True,
        is_verified=False,
    )

    with pytest.raises(AccountNotVerifiedError):
        await ComplaintService(db_session).create(
            user,
            ComplaintCreate(
                title="Pothole on Elm Street",
                description="A large pothole is damaging vehicles on Elm Street.",
                category_id=demo_category.id,
            ),
        )


@pytest.mark.asyncio
async def test_low_confidence_complaint_is_submitted_for_human_review(
    client: AsyncClient,
    user_token: str,
    demo_category,
    monkeypatch,
):
    async def classify_irrelevant_text(text: str):
        return {
            "category": "other",
            "confidence": 0.2,
            "urgency": "low",
            "is_mock": True,
            "is_relevant": False,
        }

    monkeypatch.setattr(
        "app.services.complaint_service.ai_client.classify_text",
        classify_irrelevant_text,
    )
    response = await client.post(
        "/api/v1/complaints",
        json={
            "title": "Weekend movie plans",
            "description": "I enjoy watching films with friends every weekend.",
            "category_id": str(demo_category.id),
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "submitted"
    assert response.json()["data"]["requires_human_review"] is True


@pytest.mark.asyncio
async def test_officer_can_assign_complaint_to_field_staff(
    client: AsyncClient,
    user_token: str,
    demo_category,
    db_session,
):
    officer = User(
        email="officer@example.com",
        full_name="Test Officer",
        password_hash=hash_password("Password123!"),
        roles=["officer"],
        department_id=demo_category.department_id,
        is_active=True,
        is_verified=True,
    )
    staff = User(
        email="staff@example.com",
        full_name="Test Field Staff",
        password_hash=hash_password("Password123!"),
        roles=["field_staff"],
        department_id=demo_category.department_id,
        is_active=True,
        is_verified=True,
    )
    await db_session.users.insert_one(model_to_doc(officer))
    await db_session.users.insert_one(model_to_doc(staff))

    create_res = await client.post(
        "/api/v1/complaints",
        json={
            "title": "Streetlight outage on Oak Street",
            "description": "The streetlight has been out for three nights.",
            "category_id": str(demo_category.id),
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert create_res.status_code == 200
    complaint = create_res.json()["data"]

    assign_res = await client.patch(
        f"/api/v1/complaints/{complaint['id']}/assign",
        json={
            "department_id": str(demo_category.department_id),
            "staff_id": str(staff.id),
            "notes": "Please inspect the light.",
        },
        headers={"Authorization": f"Bearer {create_access_token(str(officer.id), ['officer'])}"},
    )

    assert assign_res.status_code == 200, assign_res.text
    assert assign_res.json()["data"]["assigned_staff_id"] == str(staff.id)
    assert assign_res.json()["data"]["status"] == "assigned"

    officer_headers = {
        "Authorization": f"Bearer {create_access_token(str(officer.id), ['officer'])}"
    }
    staff_res = await client.get("/api/v1/users/staff", headers=officer_headers)
    assert staff_res.status_code == 200
    assert all(item["department_id"] == str(demo_category.department_id) for item in staff_res.json()["data"])

    foreign_department_res = await client.get(
        "/api/v1/users/staff?department_id=foreign-department",
        headers=officer_headers,
    )
    assert foreign_department_res.status_code == 403
