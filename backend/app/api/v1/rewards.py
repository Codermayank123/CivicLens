from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.mongo import utc_now
from app.dependencies import get_current_user, get_db, require_roles
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.rewards import ChallengeCreateRequest, ChallengeItem, ChallengeSubmissionItem, ChallengeSubmissionRequest, CertificateItem, LeaderboardItem, RewardAward, RewardProfile
from app.services.rewards_service import RewardsService

router = APIRouter(prefix="/rewards", tags=["Civic Hero Rewards"])


@router.get("/me", response_model=ApiResponse[RewardProfile])
async def my_rewards(current_user: User = Depends(get_current_user), db: Any = Depends(get_db)) -> ApiResponse[RewardProfile]:
    return ApiResponse(success=True, data=await RewardsService(db).profile(current_user.id))


@router.get("/leaderboard", response_model=ApiResponse[list[LeaderboardItem]])
async def leaderboard(
    scope: str = Query(default="monthly", pattern="^(monthly|city|annual)$"),
    city: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[list[LeaderboardItem]]:
    selected_city = city or (current_user.city if scope == "city" else None)
    return ApiResponse(success=True, data=await RewardsService(db).leaderboard(scope, selected_city))


@router.get("/awards", response_model=ApiResponse[list[RewardAward]])
async def awards(current_user: User = Depends(get_current_user), db: Any = Depends(get_db)) -> ApiResponse[list[RewardAward]]:
    return ApiResponse(success=True, data=await RewardsService(db).awards())


@router.get("/challenges", response_model=ApiResponse[list[ChallengeItem]])
async def challenges(current_user: User = Depends(get_current_user), db: Any = Depends(get_db)) -> ApiResponse[list[ChallengeItem]]:
    return ApiResponse(success=True, data=await RewardsService(db).challenges(current_user.id))


@router.post("/challenges", response_model=ApiResponse[ChallengeItem])
async def create_challenge(
    data: ChallengeCreateRequest,
    current_user: User = Depends(require_roles("admin")),
    db: Any = Depends(get_db),
) -> ApiResponse[ChallengeItem]:
    challenge_id = f"challenge:{data.title.lower().replace(' ', '-')[:40]}:{int(utc_now().timestamp())}"
    await db.community_challenges.insert_one({"_id": challenge_id, **data.model_dump(), "is_active": True, "created_by": current_user.id, "created_at": utc_now()})
    item = await RewardsService(db).challenges(current_user.id)
    created = next(challenge for challenge in item if challenge.id == challenge_id)
    return ApiResponse(success=True, data=created, message="Community challenge published")


@router.post("/challenges/{challenge_id}/join", response_model=ApiResponse[ChallengeItem])
async def join_challenge(challenge_id: str, current_user: User = Depends(get_current_user), db: Any = Depends(get_db)) -> ApiResponse[ChallengeItem]:
    return ApiResponse(success=True, data=await RewardsService(db).join_challenge(challenge_id, current_user.id), message="Challenge joined")


@router.post("/challenges/{challenge_id}/submit", response_model=ApiResponse[ChallengeSubmissionItem])
async def submit_challenge(
    challenge_id: str,
    data: ChallengeSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[ChallengeSubmissionItem]:
    item = await RewardsService(db).submit_challenge(challenge_id, current_user, data.evidence_urls, data.notes)
    return ApiResponse(success=True, data=item, message="Challenge evidence submitted for human review")


@router.post("/submissions/{submission_id}/review", response_model=ApiResponse[ChallengeSubmissionItem])
async def review_submission(
    submission_id: str,
    approved: bool,
    reason: str | None = None,
    current_user: User = Depends(require_roles("admin", "officer")),
    db: Any = Depends(get_db),
) -> ApiResponse[ChallengeSubmissionItem]:
    item = await RewardsService(db).verify_submission(submission_id, approved, current_user.id, reason)
    return ApiResponse(success=True, data=item, message="Challenge submission review recorded")


@router.get("/certificates", response_model=ApiResponse[list[CertificateItem]])
async def certificates(current_user: User = Depends(get_current_user), db: Any = Depends(get_db)) -> ApiResponse[list[CertificateItem]]:
    return ApiResponse(success=True, data=await RewardsService(db).certificates(current_user.id))


@router.get("/admin/overview", response_model=ApiResponse[dict])
async def admin_rewards_overview(current_user: User = Depends(require_roles("admin")), db: Any = Depends(get_db)) -> ApiResponse[dict]:
    return ApiResponse(success=True, data=await RewardsService(db).admin_overview())
