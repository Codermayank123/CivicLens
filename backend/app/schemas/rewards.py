from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RewardTransactionItem(BaseModel):
    id: str
    points: int
    action_type: str
    reference_id: str | None = None
    created_at: datetime


class RewardProfile(BaseModel):
    points: int
    tier: str
    next_tier: str | None = None
    points_to_next_tier: int = 0
    badges: list[str] = Field(default_factory=list)
    transactions: list[RewardTransactionItem] = Field(default_factory=list)


class LeaderboardItem(BaseModel):
    rank: int
    user_id: str
    full_name: str
    city: str | None = None
    points: int
    tier: str
    badges: list[str] = Field(default_factory=list)


class RewardAward(BaseModel):
    award: str
    period: str
    recipient: LeaderboardItem | None = None


class ChallengeItem(BaseModel):
    id: str
    title: str
    description: str
    challenge_type: str
    city: str | None = None
    points: int = Field(ge=0)
    start_date: datetime
    end_date: datetime
    is_active: bool = True
    participant_count: int = 0
    joined: bool = False


class ChallengeCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    challenge_type: str = Field(min_length=3, max_length=50)
    city: str | None = Field(default=None, max_length=100)
    points: int = Field(ge=1, le=1000)
    start_date: datetime
    end_date: datetime


class ChallengeSubmissionItem(BaseModel):
    id: str
    challenge_id: str
    user_id: str
    evidence_urls: list[str] = Field(default_factory=list)
    notes: str | None = None
    status: str
    points_awarded: int = 0
    created_at: datetime


class ChallengeSubmissionRequest(BaseModel):
    evidence_urls: list[str] = Field(min_length=1, max_length=5)
    notes: str | None = Field(default=None, max_length=2000)


class CertificateItem(BaseModel):
    id: str
    title: str
    issued_for: str
    certificate_hash: str
    issued_at: datetime
