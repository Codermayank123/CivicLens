"""
CivicLens — Security Core

JWT token creation/verification, password hashing, and auth utilities.
Uses Argon2id for password hashing (OWASP recommended).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from jose import JWTError, jwt

from app.config import get_settings
from app.exceptions import TokenExpiredError, TokenInvalidError

settings = get_settings()
ph = PasswordHasher()


# ── Password Hashing ────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against an Argon2id hash."""
    try:
        return ph.verify(password_hash, password)
    except VerificationError:
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """Check if a password hash needs to be rehashed with updated parameters."""
    return ph.check_needs_rehash(password_hash)


# ── JWT Tokens ───────────────────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    roles: list[str],
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user_id,
        "roles": roles,
        "type": "access",
        "iat": now,
        "exp": expires,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, datetime]:
    """Create a long-lived refresh token. Returns (token, expiry)."""
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": expires,
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token. Raises on expiry or invalid signature."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        error_str = str(e).lower()
        if "expired" in error_str:
            raise TokenExpiredError()
        raise TokenInvalidError()


def create_verification_token() -> str:
    """Create a random token for email verification or password reset."""
    return str(uuid.uuid4())
