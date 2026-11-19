"""
CivicLens Backend — Application Configuration

Configures application settings from environment variables.
Uses MongoDB exclusively as the primary database.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV_FILE = PROJECT_ROOT / "backend" / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        # Load shared development values first, then backend-specific values.
        # Pydantic-settings gives later env files precedence; the OS process
        # environment still has the highest precedence.
        env_file=(PROJECT_ROOT / ".env", BACKEND_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── General ──────────────────────────────────────────────────────────────
    APP_NAME: str = "CivicLens"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ── Server ───────────────────────────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_WORKERS: int = 1
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "local_dev_secret_1234567890abcdefghijklmnopqrstuvwxyz"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── MongoDB (Exclusive Primary Database) ──────────────────────────────────
    # ``MONGO_URI`` is accepted as a compatibility alias, but there is no
    # implicit local-database fallback. A missing URI makes readiness fail.
    MONGODB_URL: str = Field(
        default="",
        validation_alias=AliasChoices("MONGODB_URL", "MONGO_URI"),
    )
    MONGODB_DB_NAME: str = "civiclens"
    MONGODB_MAX_POOL_SIZE: int = 50
    MONGODB_MIN_POOL_SIZE: int = 5

    # ── Redis (Optional) ─────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_ENABLED: bool = False

    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # ── S3 / MinIO Object Storage ────────────────────────────────────────────
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "civiclens-media"
    S3_REGION: str = "us-east-1"
    S3_PUBLIC_URL: str = "http://localhost:9000/civiclens-media"
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    BACKEND_PUBLIC_URL: str = "http://localhost:8000"
    MEDIA_SIGNING_SECRET: str = "local_dev_signing_secret_1234567890abcdefghijklmnopqrstuvwxyz"

    # ── AI Service ───────────────────────────────────────────────────────────
    AI_SERVICE_URL: str = "http://localhost:8001"
    # Real-provider mode is the safe default. Mock mode is opt-in for isolated
    # tests only and is rejected by production configuration validation.
    AI_MOCK_MODE: bool = False
    AI_CLIENT_TIMEOUT_SECONDS: float = 60.0

    # ── Identity verification ────────────────────────────────────────────────
    IDENTITY_PROVIDER: Literal[
        "disabled",
        "development",
        "uidai_sandbox",
        "uidai_offline_ekyc",
    ] = "development"
    IDENTITY_CONSENT_VERSION: str = "2026-01"
    CITIZEN_REGISTRATION_ENABLED: bool = False
    UIDAI_SANDBOX_AUTH_URL: str = "https://developer.uidai.gov.in/authserver/2.5"
    UIDAI_SANDBOX_OTP_URL: str = "https://developer.uidai.gov.in/uidotp/2.5"
    UIDAI_SANDBOX_EKYC_URL: str = "https://developer.uidai.gov.in/uidkyc/kyc/2.5"
    UIDAI_AUA_CODE: str = ""
    UIDAI_LICENSE_KEY: str = ""
    UIDAI_OFFLINE_EKYC_CERT_PATH: str = ""

    # ── Email ────────────────────────────────────────────────────────────────
    EMAIL_PROVIDER: str = "mock"
    BREVO_API_KEY: str = ""
    BREVO_SENDER_EMAIL: str = ""
    BREVO_SENDER_NAME: str = "CivicLens"
    BREVO_WEBHOOK_SECRET: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@civiclens.local"
    EMAIL_REPLY_TO: str = ""
    FRONTEND_PUBLIC_URL: str = "http://localhost:5173"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60
    SMS_PROVIDER: str = "mock"
    MESSAGE_CENTRAL_CUSTOMER_ID: str = ""
    MESSAGE_CENTRAL_AUTH_TOKEN: str = ""
    MESSAGE_CENTRAL_BASE_URL: str = "https://cpaas.messagecentral.com"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    OTP_EXPIRY_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_SESSION_TTL_MINUTES: int = 15
    OTP_RATE_LIMIT_WINDOW_MINUTES: int = 60
    OTP_MAX_REQUESTS_PER_WINDOW: int = 5
    ALLOW_RESOLUTION_WITHOUT_EVIDENCE: bool = False
    MAX_RESOLUTION_EMAIL_ATTACHMENT_BYTES: int = 12 * 1024 * 1024

    # Geocoding and accountability automation. The default uses the public
    # Nominatim endpoint for development only; production deployments should
    # provide an approved provider and a descriptive User-Agent.
    GEOCODING_PROVIDER: str = "nominatim"
    GEOCODING_URL: str = "https://nominatim.openstreetmap.org/reverse"
    GEOCODING_USER_AGENT: str = "CivicLens/1.0 (development)"
    # A maintained India state/district/sub-district catalog must be supplied
    # by deployment configuration. The application never ships a partial list.
    INDIA_LOCATION_DATA_URL: str = ""
    DEADLINE_SCAN_INTERVAL_SECONDS: int = 300
    DEADLINE_REMINDER_HOURS: int = 24
    ESCALATION_REPEAT_HOURS: int = 24

    # ── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10

    @field_validator("DEBUG", mode="before")
    @classmethod
    def coerce_debug_flag(cls, value: object) -> bool:
        """Treat common release-style launcher values as a safe false flag.

        Some process managers inject ``DEBUG=release``. Pydantic otherwise
        aborts before the application can report its actual configuration.
        Unknown values fail closed to ``False``.
        """
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on", "debug"}:
            return True
        return False

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if not self.is_production:
            return self

        problems = []
        if self.DEBUG:
            problems.append("DEBUG must be false")
        if len(self.JWT_SECRET_KEY) < 64 or "CHANGE_ME" in self.JWT_SECRET_KEY.upper():
            problems.append("JWT_SECRET_KEY must be a unique secret of at least 64 characters")
        if len(self.MEDIA_SIGNING_SECRET) < 64 or "CHANGE_ME" in self.MEDIA_SIGNING_SECRET.upper():
            problems.append("MEDIA_SIGNING_SECRET must be a unique secret of at least 64 characters")
        if any(host in self.MONGODB_URL.lower() for host in ("localhost", "127.0.0.1", "::1")):
            problems.append("MONGODB_URL must point to a secure hosted MongoDB instance in production")
        if not self.MONGODB_URL.strip():
            problems.append("MONGODB_URL or MONGO_URI is required")
        if self.S3_ACCESS_KEY == "minioadmin" or self.S3_SECRET_KEY == "minioadmin":
            problems.append("S3 credentials must not use MinIO defaults")
        if self.STORAGE_BACKEND != "s3":
            problems.append("STORAGE_BACKEND must be s3 in production")
        if self.AI_MOCK_MODE:
            problems.append("AI_MOCK_MODE must be false")
        email_provider = self.EMAIL_PROVIDER.strip().lower()
        if email_provider != "brevo":
            problems.append("EMAIL_PROVIDER must use a real delivery provider; production requires brevo")
        if email_provider == "brevo" and not all(
            value.strip() for value in (self.BREVO_API_KEY, self.BREVO_SENDER_EMAIL, self.BREVO_SENDER_NAME)
        ):
            problems.append("BREVO_API_KEY, BREVO_SENDER_EMAIL and BREVO_SENDER_NAME are required when EMAIL_PROVIDER=brevo")
        if email_provider == "smtp" and not self.SMTP_HOST.strip():
            problems.append("SMTP_HOST is required when EMAIL_PROVIDER=smtp")
        if email_provider == "resend" and not self.RESEND_API_KEY.strip():
            problems.append("RESEND_API_KEY is required when EMAIL_PROVIDER=resend")
        sms_provider = self.SMS_PROVIDER.strip().lower()
        if sms_provider != "message_central":
            problems.append("SMS_PROVIDER must use a real delivery provider; production requires message_central")
        if sms_provider == "message_central" and not all(
            value.strip() for value in (self.MESSAGE_CENTRAL_CUSTOMER_ID, self.MESSAGE_CENTRAL_AUTH_TOKEN, self.MESSAGE_CENTRAL_BASE_URL)
        ):
            problems.append("Message Central credentials and base URL are required when SMS_PROVIDER=message_central")
        if sms_provider == "twilio" and not all(
            value.strip()
            for value in (self.TWILIO_ACCOUNT_SID, self.TWILIO_AUTH_TOKEN, self.TWILIO_FROM_NUMBER)
        ):
            problems.append("Twilio credentials and TWILIO_FROM_NUMBER are required when SMS_PROVIDER=twilio")
        if self.CITIZEN_REGISTRATION_ENABLED:
            if self.IDENTITY_PROVIDER in {"disabled", "development"}:
                problems.append(
                    "CITIZEN_REGISTRATION_ENABLED requires a UIDAI-authorized identity provider"
                )
            if self.IDENTITY_PROVIDER == "uidai_sandbox":
                problems.append(
                    "UIDAI sandbox is not production-ready and cannot enable citizen registration"
                )
            if self.IDENTITY_PROVIDER == "uidai_offline_ekyc":
                problems.append(
                    "Offline e-KYC signature verification is not implemented and cannot enable "
                    "production citizen registration"
                )
            if self.IDENTITY_PROVIDER == "uidai_sandbox" and (
                not self.UIDAI_AUA_CODE.strip() or not self.UIDAI_LICENSE_KEY.strip()
            ):
                problems.append("UIDAI sandbox credentials are required for citizen registration")
            if self.IDENTITY_PROVIDER == "uidai_offline_ekyc" and not self.UIDAI_OFFLINE_EKYC_CERT_PATH.strip():
                problems.append("UIDAI_OFFLINE_EKYC_CERT_PATH is required for offline e-KYC registration")
        if any(not origin.startswith("https://") for origin in self.cors_origins_list):
            problems.append("BACKEND_CORS_ORIGINS must contain only HTTPS origins")
        if not self.BACKEND_PUBLIC_URL.startswith("https://"):
            problems.append("BACKEND_PUBLIC_URL must use HTTPS")

        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def citizen_registration_enabled(self) -> bool:
        if self.is_production:
            return self.CITIZEN_REGISTRATION_ENABLED
        return self.IDENTITY_PROVIDER != "disabled"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
