"""MongoDB-backed Civic Hero rewards, challenges, and leaderboards."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.user import CivicTier, User
from app.schemas.rewards import (
    CertificateItem,
    ChallengeItem,
    ChallengeSubmissionItem,
    LeaderboardItem,
    RewardAward,
    RewardProfile,
    RewardTransactionItem,
)


class RewardsService:
    def __init__(self, db: Any):
        self.db = db

    async def profile(self, user_id: str) -> RewardProfile:
        user = await self.db.users.find_one({"_id": user_id, "deleted_at": None})
        if not user:
            raise NotFoundError("User not found")
        points = int(user.get("civic_points", 0))
        tier = CivicTier.from_points(points)
        next_tier, points_to_next = _next_tier(points)
        docs = await self.db.points_transactions.find({"user_id": user_id}).sort("created_at", -1).limit(100).to_list(length=100)
        badges = sorted(set(user.get("badges", []) + _derived_badges(points)))
        transactions = [RewardTransactionItem(id=str(item["_id"]), points=item["points"], action_type=item["action_type"], reference_id=item.get("reference_id"), created_at=item["created_at"]) for item in docs]
        return RewardProfile(points=points, tier=tier.value, next_tier=next_tier.value if next_tier else None, points_to_next_tier=points_to_next, badges=badges, transactions=transactions)

    async def leaderboard(self, scope: str, city: str | None = None, limit: int = 25) -> list[LeaderboardItem]:
        now = datetime.now(timezone.utc)
        start = datetime(now.year, 1, 1, tzinfo=timezone.utc) if scope == "annual" else datetime(now.year, now.month, 1, tzinfo=timezone.utc) if scope == "monthly" else None
        users = await self.db.users.find({"deleted_at": None, "roles": "citizen"}).to_list(length=10000)
        if city:
            users = [item for item in users if item.get("city", "").lower() == city.lower()]
        totals: dict[str, int] = {}
        if start:
            transactions = await self.db.points_transactions.find({"created_at": {"$gte": start}}).to_list(length=100000)
            for item in transactions:
                totals[item["user_id"]] = totals.get(item["user_id"], 0) + int(item.get("points", 0))
        rows = []
        for item in users:
            points = totals.get(item["_id"], 0) if start else int(item.get("civic_points", 0))
            rows.append((points, item))
        rows.sort(key=lambda pair: (-pair[0], pair[1].get("full_name", "")))
        return [LeaderboardItem(rank=index, user_id=item["_id"], full_name=item["full_name"], city=item.get("city"), points=points, tier=CivicTier.from_points(points).value, badges=sorted(set(item.get("badges", []) + _derived_badges(points)))) for index, (points, item) in enumerate(rows[:limit], start=1)]

    async def awards(self) -> list[RewardAward]:
        monthly = await self.leaderboard("monthly", limit=1)
        annual = await self.leaderboard("annual", limit=1)
        return [
            RewardAward(award="Citizen of the Month", period=datetime.now(timezone.utc).strftime("%Y-%m"), recipient=monthly[0] if monthly else None),
            RewardAward(award="Citizen of the Year", period=str(datetime.now(timezone.utc).year), recipient=annual[0] if annual else None),
        ]

    async def challenges(self, user_id: str) -> list[ChallengeItem]:
        docs = await self.db.community_challenges.find({"is_active": True}).sort("start_date", 1).to_list(length=100)
        joined = {item["challenge_id"] for item in await self.db.challenge_participations.find({"user_id": user_id}).to_list(length=1000)}
        result = []
        for item in docs:
            count = await self.db.challenge_participations.count_documents({"challenge_id": item["_id"]})
            result.append(ChallengeItem(id=item["_id"], title=item["title"], description=item["description"], challenge_type=item["challenge_type"], city=item.get("city"), points=int(item.get("points", 0)), start_date=item["start_date"], end_date=item["end_date"], is_active=item.get("is_active", True), participant_count=count, joined=item["_id"] in joined))
        return result

    async def join_challenge(self, challenge_id: str, user_id: str) -> ChallengeItem:
        challenge = await self.db.community_challenges.find_one({"_id": challenge_id, "is_active": True})
        if not challenge:
            raise NotFoundError("Community challenge not found or inactive")
        existing = await self.db.challenge_participations.find_one({"challenge_id": challenge_id, "user_id": user_id})
        if existing:
            raise ConflictError("You have already joined this challenge")
        await self.db.challenge_participations.insert_one({"_id": f"{challenge_id}:{user_id}", "challenge_id": challenge_id, "user_id": user_id, "created_at": datetime.now(timezone.utc)})
        count = await self.db.challenge_participations.count_documents({"challenge_id": challenge_id})
        return ChallengeItem(id=challenge["_id"], title=challenge["title"], description=challenge["description"], challenge_type=challenge["challenge_type"], city=challenge.get("city"), points=int(challenge.get("points", 0)), start_date=challenge["start_date"], end_date=challenge["end_date"], is_active=True, participant_count=count, joined=True)

    async def submit_challenge(self, challenge_id: str, user: User, evidence_urls: list[str], notes: str | None) -> ChallengeSubmissionItem:
        challenge = await self.db.community_challenges.find_one({"_id": challenge_id, "is_active": True})
        if not challenge:
            raise NotFoundError("Community challenge not found or inactive")
        participation = await self.db.challenge_participations.find_one({"challenge_id": challenge_id, "user_id": user.id})
        if not participation:
            raise ValidationError("Join the challenge before submitting evidence")
        for url in evidence_urls:
            from app.services.storage_service import is_managed_media_url
            if not is_managed_media_url(url):
                raise ValidationError("Challenge evidence must be uploaded through CivicLens")
        item = {"_id": f"submission:{challenge_id}:{user.id}:{datetime.now(timezone.utc).timestamp()}", "challenge_id": challenge_id, "user_id": user.id, "evidence_urls": evidence_urls, "notes": notes, "status": "pending_review", "points_awarded": 0, "created_at": datetime.now(timezone.utc)}
        await self.db.challenge_submissions.insert_one(item)
        return ChallengeSubmissionItem(id=item["_id"], challenge_id=item["challenge_id"], user_id=item["user_id"], evidence_urls=item["evidence_urls"], notes=item.get("notes"), status=item["status"], points_awarded=item["points_awarded"], created_at=item["created_at"])

    async def verify_submission(self, submission_id: str, approved: bool, reviewer_id: str, reason: str | None = None) -> ChallengeSubmissionItem:
        submission = await self.db.challenge_submissions.find_one({"_id": submission_id})
        if not submission:
            raise NotFoundError("Challenge submission not found")
        if submission.get("status") != "pending_review":
            raise ValidationError("This challenge submission has already been reviewed")
        challenge = await self.db.community_challenges.find_one({"_id": submission["challenge_id"]})
        status = "approved" if approved else "rejected"
        points = int(challenge.get("points", 0)) if approved and challenge else 0
        await self.db.challenge_submissions.update_one({"_id": submission_id}, {"$set": {"status": status, "points_awarded": points, "reviewed_by": reviewer_id, "review_reason": reason, "reviewed_at": datetime.now(timezone.utc)}})
        if approved and points:
            await self.award_points(submission["user_id"], points, "challenge_verified", submission_id)
            await self._issue_certificate(submission["user_id"], challenge["title"], submission_id)
        submission.update({"status": status, "points_awarded": points})
        return ChallengeSubmissionItem(id=submission["_id"], challenge_id=submission["challenge_id"], user_id=submission["user_id"], evidence_urls=submission["evidence_urls"], notes=submission.get("notes"), status=submission["status"], points_awarded=submission["points_awarded"], created_at=submission["created_at"])

    async def award_points(self, user_id: str, points: int, action_type: str, reference_id: str) -> bool:
        # The transaction document's natural _id is the idempotency key, so a
        # concurrent duplicate insert raises DuplicateKeyError instead of
        # awarding points twice.
        transaction = {
            "_id": f"{user_id}:{action_type}:{reference_id}",
            "user_id": user_id,
            "points": points,
            "action_type": action_type,
            "reference_id": reference_id,
            "created_at": datetime.now(timezone.utc),
        }
        user = await self.db.users.find_one({"_id": user_id})
        if not user:
            return False
        # Keep the in-memory/test adapter behavior aligned with Mongo's unique
        # idempotency key. The unique index remains the race-safe guard in Atlas.
        if await self.db.points_transactions.find_one({"_id": transaction["_id"]}):
            return False
        try:
            await self.db.points_transactions.insert_one(transaction)
        except DuplicateKeyError:
            return False
        new_points = int(user.get("civic_points", 0)) + points
        tier = CivicTier.from_points(new_points)
        await self.db.users.update_one({"_id": user_id}, {"$inc": {"civic_points": points}, "$set": {"civic_tier": tier.value, "updated_at": datetime.now(timezone.utc)}})
        return True

    async def certificates(self, user_id: str) -> list[CertificateItem]:
        docs = await self.db.certificates.find({"user_id": user_id}).sort("issued_at", -1).to_list(length=100)
        return [CertificateItem(id=item["_id"], title=item["title"], issued_for=item["issued_for"], certificate_hash=item["certificate_hash"], issued_at=item["issued_at"]) for item in docs]

    async def admin_overview(self) -> dict[str, Any]:
        users = await self.db.users.find({"roles": "citizen", "deleted_at": None}).to_list(length=10000)
        transactions = await self.db.points_transactions.find({}).sort("created_at", -1).limit(5000).to_list(length=5000)
        return {
            "citizens_with_points": sum(int(item.get("civic_points", 0)) > 0 for item in users),
            "total_points_awarded": sum(int(item.get("points", 0)) for item in transactions),
            "verified_contribution_count": sum(item.get("action_type") in {"verified_report", "validated_support", "challenge_verified"} for item in transactions),
            "transaction_count": len(transactions),
            "recent_allocations": [{"id": item["_id"], "user_id": item["user_id"], "points": item.get("points", 0), "action_type": item.get("action_type"), "reference_id": item.get("reference_id"), "created_at": item.get("created_at")} for item in transactions[:50]],
        }

    async def _issue_certificate(self, user_id: str, title: str, reference_id: str) -> None:
        existing = await self.db.certificates.find_one({"user_id": user_id, "issued_for": reference_id})
        if existing:
            return
        now = datetime.now(timezone.utc)
        cert_id = f"certificate:{user_id}:{reference_id}"
        digest = hashlib.sha256(f"{cert_id}:{title}:{now.isoformat()}".encode()).hexdigest()
        await self.db.certificates.insert_one({"_id": cert_id, "user_id": user_id, "title": f"Civic Hero Certificate — {title}", "issued_for": reference_id, "certificate_hash": digest, "issued_at": now})


def _next_tier(points: int) -> tuple[CivicTier | None, int]:
    for tier, threshold in ((CivicTier.SILVER, 100), (CivicTier.GOLD, 300), (CivicTier.PLATINUM, 700)):
        if points < threshold:
            return tier, threshold - points
    return None, 0


def _derived_badges(points: int) -> list[str]:
    badges = ["First Report"] if points >= 50 else []
    if points >= 100:
        badges.append("Community Builder")
    if points >= 300:
        badges.append("Civic Champion")
    if points >= 700:
        badges.append("Civic Legend")
    return badges
