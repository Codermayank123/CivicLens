"""
CivicLens — Analytics Integration Tests
"""

import pytest
from httpx import AsyncClient

from app.core import create_access_token, hash_password
from app.models.user import User
from app.core.mongo import model_to_doc


@pytest.mark.asyncio
async def test_analytics_overview_and_heatmap(client: AsyncClient, db_session):
    anonymous_response = await client.get("/api/v1/analytics/overview")
    assert anonymous_response.status_code == 401

    admin = User(
        email="analytics-admin@example.com",
        full_name="Analytics Admin",
        password_hash=hash_password("Password123!"),
        roles=["admin"],
        is_active=True,
        is_verified=True,
    )
    await db_session.users.insert_one(model_to_doc(admin))
    headers = {"Authorization": f"Bearer {create_access_token(str(admin.id), ['admin'])}"}

    # 1. Fetch Overview Stats
    res = await client.get("/api/v1/analytics/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "total_complaints" in data["data"]
    assert "status_distribution" in data["data"]
    assert "trends_last_30_days" in data["data"]
    assert data["data"]["total_complaints"] == 0
    assert data["data"]["active_field_staff"] == 0
    assert data["data"]["duplicate_prevented_count"] == 0
    assert data["data"]["citizen_satisfaction_percentage"] == 0
    assert len(data["data"]["trends_last_30_days"]) == 30
    assert all(point["reported"] == 0 and point["resolved"] == 0 for point in data["data"]["trends_last_30_days"])

    # 2. Fetch Heatmap Points
    heatmap_res = await client.get("/api/v1/analytics/heatmap", headers=headers)
    assert heatmap_res.status_code == 200
    heatmap_data = heatmap_res.json()
    assert heatmap_data["success"] is True
    assert isinstance(heatmap_data["data"], list)
