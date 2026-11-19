"""
CivicLens — Authentication Schemas
Validation and serialization models for auth endpoints.
"""

from __future__ import annotations

import re

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic import field_validator


def validate_password_strength(value: str) -> str:
    """Apply one password policy consistently to every password entry point."""
    if len(value) < 10:
        raise ValueError("Password must be at least 10 characters")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain an uppercase letter")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain a lowercase letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain a number")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Password must contain a special character")
    return value


class UserBrief(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None
    roles: list[str] = Field(default_factory=list)
    department_id: str | None = None
    department_name: str | None = None
    city: str | None = None
    is_active: bool = True
    is_verified: bool = False
    email_verified: bool = False
    mobile_verified: bool = False
    identity_verified: bool = False
    email_notifications: bool = True
    sms_notifications: bool = True

    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    verification_session_id: str = Field(min_length=16, max_length=128)
    verification_token: str = Field(min_length=32, max_length=256)

    _password_strength = field_validator("password")(validate_password_strength)

    @field_validator("phone")
    @classmethod
    def normalize_e164_phone(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = re.sub(r"[\s().-]", "", value.strip())
        if normalized.startswith("00"):
            normalized = "+" + normalized[2:]
        if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized):
            raise ValueError("Phone number must be a valid international E.164 number")
        return normalized


class RegistrationOtpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    verification_method: Literal["email", "sms"]

    _password_strength = field_validator("password")(validate_password_strength)

    @field_validator("phone")
    @classmethod
    def normalize_registration_phone(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = re.sub(r"[\s().-]", "", value.strip())
        if normalized.startswith("00"):
            normalized = "+" + normalized[2:]
        if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized):
            raise ValueError("Phone number must be a valid international E.164 number")
        return normalized


class VerifyRegistrationOtpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verification_session_id: str = Field(min_length=16, max_length=128)
    verification_token: str = Field(min_length=32, max_length=256)
    code: str = Field(pattern=r"^\d{4,8}$")


class CompleteRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verification_session_id: str = Field(min_length=16, max_length=128)
    verification_token: str = Field(min_length=32, max_length=256)


class NotificationPreferencesUpdate(BaseModel):
    email_notifications: bool | None = None
    sms_notifications: bool | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int
    user: UserBrief


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)

    _password_strength = field_validator("new_password")(validate_password_strength)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

    _password_strength = field_validator("new_password")(validate_password_strength)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=16, max_length=256)


class RequestPhoneOtpRequest(BaseModel):
    """Request a verification code for the currently authenticated user's phone."""

    phone: str | None = Field(default=None, max_length=20)


class VerifyPhoneOtpRequest(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")


class CreateStaffRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    role: str = Field(pattern="^(officer|field_staff|admin)$")
    department_id: str | None = None

    _password_strength = field_validator("password")(validate_password_strength)

    @field_validator("phone")
    @classmethod
    def normalize_staff_phone(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        normalized = re.sub(r"[\s().-]", "", value.strip())
        if normalized.startswith("00"):
            normalized = "+" + normalized[2:]
        if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized):
            raise ValueError("Phone number must be a valid international E.164 number")
        return normalized
