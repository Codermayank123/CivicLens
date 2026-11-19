"""
CivicLens — User & Auth MongoDB Models

Stores citizen, officer, field staff, and admin accounts.
Supports role-based access, Civic Hero points/tiers, and session revocation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class UserRoleType(str, Enum):
    CITIZEN = "citizen"
    OFFICER = "officer"
    FIELD_STAFF = "field_staff"
    ADMIN = "admin"


class CivicTier(str, Enum):
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"
    PLATINUM = "Platinum"

    @classmethod
    def from_points(cls, points: int) -> CivicTier:
        if points >= 700:
            return cls.PLATINUM
        if points >= 300:
            return cls.GOLD
        if points >= 100:
            return cls.SILVER
        return cls.BRONZE


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    phone: str | None = None
    full_name: str
    password_hash: str
    avatar_url: str | None = None
    roles: list[str] = Field(default_factory=lambda: ["citizen"])
    department_id: str | None = None
    city: str | None = None

    # Status & verification
    is_active: bool = True
    email_verified: bool = False
    mobile_verified: bool = False
    is_verified: bool = False
    identity_verified: bool = False
    identity_provider: str | None = None
    is_suspended: bool = False
    suspended_reason: str | None = None

    # Accessibility & preferences
    preferred_language: str = "en"
    high_contrast_mode: bool = False
    reduced_motion: bool = False
    email_notifications: bool = True
    sms_notifications: bool = True

    # Civic Hero Gamification
    civic_points: int = 0
    civic_tier: CivicTier = CivicTier.BRONZE
    badges: list[str] = Field(default_factory=list)

    # Security & MFA
    mfa_enabled: bool = False
    mfa_secret: str | None = None

    # Tokens
    verification_token: str | None = None
    verification_token_expires: datetime | None = None
    reset_token: str | None = None
    reset_token_expires: datetime | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at: datetime | None = None
    deleted_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def map_mongo_id(cls, value: Any) -> Any:
        if isinstance(value, dict) and "_id" in value and "id" not in value:
            value = dict(value)
            value["id"] = str(value.pop("_id"))
        return value

    def has_role(self, *role_names: str) -> bool:
        """Check if user has any of the specified roles or is admin."""
        if "admin" in self.roles:
            return True
        return any(role in self.roles for role in role_names)

    def update_tier(self) -> None:
        """Update tier based on current civic points."""
        self.civic_tier = CivicTier.from_points(self.civic_points)


class RefreshToken(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    token_hash: str
    expires_at: datetime
    revoked: bool = False
    revoked_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_agent: str | None = None
    ip_address: str | None = None
