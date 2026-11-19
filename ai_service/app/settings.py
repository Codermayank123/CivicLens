from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ENV_FILE = PROJECT_ROOT / "ai_service" / ".env"


class AISettings(BaseSettings):
    # Shared values are overridden by the AI-service environment file. The
    # process environment remains the highest-precedence source.
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", AI_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Real-provider mode is the default. Mock mode must be explicitly enabled
    # for isolated tests and is never a production execution path.
    AI_MOCK_MODE: bool = False
    AI_PROVIDER: Literal["mock", "openai_compatible"] = "openai_compatible"
    AI_API_KEY: str = ""
    AI_API_BASE_URL: str = "https://api.openai.com/v1"
    AI_TEXT_MODEL: str = "gpt-4o-mini"
    AI_VISION_MODEL: str = "gpt-4o-mini"
    AI_REQUEST_TIMEOUT_SECONDS: float = 45.0
    AI_REVIEW_CONFIDENCE_THRESHOLD: float = 0.5
    AI_MODEL_VERSION: str = "civiclens-ai-1"
    AI_SERVICE_HOST: str = "0.0.0.0"
    AI_SERVICE_PORT: int = 8001

    @field_validator("AI_API_BASE_URL", mode="after")
    @classmethod
    def normalize_provider_base_url(cls, value: str) -> str:
        """Normalize Google's OpenAI-compatible root to its API base path."""
        normalized = value.rstrip("/")
        if normalized == "https://generativelanguage.googleapis.com":
            return f"{normalized}/v1beta/openai"
        return normalized

    @model_validator(mode="after")
    def validate_real_mode(self) -> AISettings:
        if self.AI_MOCK_MODE:
            return self
        if self.AI_PROVIDER != "openai_compatible":
            raise ValueError("AI_PROVIDER must be openai_compatible when AI_MOCK_MODE is false")
        if not self.AI_API_KEY.strip():
            raise ValueError("AI_API_KEY is required when AI_MOCK_MODE is false")
        return self
