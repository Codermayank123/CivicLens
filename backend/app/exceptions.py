"""
CivicLens Backend — Structured Exception Handling

All custom exceptions inherit from CivicLensError and carry an error code,
HTTP status, and optional details dict. The exception handler in main.py
converts these into the standard JSON error envelope.
"""

from __future__ import annotations

from typing import Any


class CivicLensError(Exception):
    """Base exception for all CivicLens application errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)


# ── Authentication ───────────────────────────────────────────────────────────

class AuthenticationError(CivicLensError):
    status_code = 401
    error_code = "AUTHENTICATION_FAILED"
    message = "Invalid credentials"

class AuthenticationFailedError(AuthenticationError):
    """Raised when authentication fails."""
    pass
class TokenExpiredError(CivicLensError):
    status_code = 401
    error_code = "TOKEN_EXPIRED"
    message = "Access token has expired"


class TokenInvalidError(CivicLensError):
    status_code = 401
    error_code = "TOKEN_INVALID"
    message = "Invalid or malformed token"


class RefreshTokenError(CivicLensError):
    status_code = 401
    error_code = "REFRESH_TOKEN_INVALID"
    message = "Refresh token is invalid or has been revoked"


# ── Authorization ────────────────────────────────────────────────────────────

class ForbiddenError(CivicLensError):
    status_code = 403
    error_code = "FORBIDDEN"
    message = "You do not have permission to perform this action"


class InsufficientRoleError(CivicLensError):
    status_code = 403
    error_code = "INSUFFICIENT_ROLE"
    message = "Your role does not permit this operation"


# ── Resources ────────────────────────────────────────────────────────────────

class NotFoundError(CivicLensError):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "The requested resource was not found"


class ComplaintNotFoundError(CivicLensError):
    status_code = 404
    error_code = "COMPLAINT_NOT_FOUND"
    message = "The requested complaint does not exist"


class UserNotFoundError(CivicLensError):
    status_code = 404
    error_code = "USER_NOT_FOUND"
    message = "The requested user does not exist"


class DepartmentNotFoundError(CivicLensError):
    status_code = 404
    error_code = "DEPARTMENT_NOT_FOUND"
    message = "The requested department does not exist"


# ── Validation & Conflict ────────────────────────────────────────────────────

class ValidationError(CivicLensError):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Request validation failed"


class ConflictError(CivicLensError):
    status_code = 409
    error_code = "CONFLICT"
    message = "Resource already exists"


class DuplicateEmailError(CivicLensError):
    status_code = 409
    error_code = "DUPLICATE_EMAIL"
    message = "An account with this email already exists"


# ── File Upload ──────────────────────────────────────────────────────────────

class FileUploadError(CivicLensError):
    status_code = 400
    error_code = "FILE_UPLOAD_ERROR"
    message = "File upload failed"


class FileTooLargeError(CivicLensError):
    status_code = 413
    error_code = "FILE_TOO_LARGE"
    message = "File exceeds the maximum allowed size"


class InvalidFileTypeError(CivicLensError):
    status_code = 400
    error_code = "INVALID_FILE_TYPE"
    message = "File type is not allowed"


# ── Rate Limiting ────────────────────────────────────────────────────────────

class RateLimitError(CivicLensError):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please try again later"


# ── External Services ───────────────────────────────────────────────────────

class AIServiceError(CivicLensError):
    status_code = 502
    error_code = "AI_SERVICE_ERROR"
    message = "AI service is temporarily unavailable"


class ProviderUnavailableError(CivicLensError):
    status_code = 503
    error_code = "PROVIDER_UNAVAILABLE"
    message = "The requested delivery provider is temporarily unavailable"


class StorageServiceError(CivicLensError):
    status_code = 502
    error_code = "STORAGE_SERVICE_ERROR"
    message = "Storage service is temporarily unavailable"


# ── Account ──────────────────────────────────────────────────────────────────

class AccountSuspendedError(CivicLensError):
    status_code = 403
    error_code = "ACCOUNT_SUSPENDED"
    message = "Your account has been suspended"


class AccountNotVerifiedError(CivicLensError):
    status_code = 403
    error_code = "ACCOUNT_NOT_VERIFIED"
    message = "Complete identity verification before submitting complaints"


class IdentityVerificationUnavailableError(CivicLensError):
    status_code = 503
    error_code = "IDENTITY_VERIFICATION_UNAVAILABLE"
    message = "Citizen registration is unavailable until an authorized identity verification provider is configured"
