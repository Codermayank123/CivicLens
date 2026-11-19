import pytest
from httpx import AsyncClient
from pymongo.errors import DuplicateKeyError

from app.core import create_access_token
from app.services.rewards_service import RewardsService


@pytest.mark.asyncio
async def test_rewards_and_public_accountability_are_database_backed(
    client: AsyncClient,
    demo_user,
    demo_category,
):
    headers = {"Authorization": f"Bearer {create_access_token(demo_user.id, ['citizen'])}"}

    profile = await client.get("/api/v1/rewards/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["data"]["points"] == 0
    assert profile.json()["data"]["tier"] == "Bronze"

    leaderboard = await client.get("/api/v1/rewards/leaderboard?scope=annual", headers=headers)
    assert leaderboard.status_code == 200
    assert leaderboard.json()["data"][0]["user_id"] == demo_user.id

    accountability = await client.get("/api/v1/public/accountability")
    assert accountability.status_code == 200
    assert accountability.json()["data"][0]["total_complaints"] == 0

    heatmap = await client.get("/api/v1/public/heatmap")
    assert heatmap.status_code == 200
    assert heatmap.json()["data"] == []


class _UniqueCollection:
    """Collection stub enforcing unique _id the way MongoDB does."""

    def __init__(self, documents: list[dict]):
        self.documents = documents

    async def insert_one(self, document: dict):
        if any(doc["_id"] == document["_id"] for doc in self.documents):
            raise DuplicateKeyError("duplicate key error")
        self.documents.append(document)

    async def find_one(self, query: dict):
        return next((doc for doc in self.documents if all(doc.get(k) == v for k, v in query.items())), None)

    async def count_documents(self, query: dict):
        return sum(1 for doc in self.documents if all(doc.get(k) == v for k, v in query.items()))


@pytest.mark.asyncio
async def test_award_points_is_idempotent_under_race(db_session, demo_user):
    service = RewardsService(db_session)
    complaint_id = "complaint-race"

    assert await service.award_points(demo_user.id, 50, "verified_report", complaint_id) is True
    assert await service.award_points(demo_user.id, 50, "verified_report", complaint_id) is False

    user = await db_session.users.find_one({"_id": demo_user.id})
    assert user["civic_points"] == 50


@pytest.mark.asyncio
async def test_award_points_never_awards_when_transaction_insert_conflicts(db_session, demo_user):
    service = RewardsService(db_session)
    complaint_id = "complaint-conflict"
    conflict = _UniqueCollection(
        [{"_id": f"{demo_user.id}:verified_report:{complaint_id}"}]
    )
    service.db.points_transactions = conflict  # type: ignore[assignment]

    assert await service.award_points(demo_user.id, 50, "verified_report", complaint_id) is False

    user = await db_session.users.find_one({"_id": demo_user.id})
    assert user["civic_points"] == 0
