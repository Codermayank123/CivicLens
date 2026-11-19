from __future__ import annotations

from app.mock_provider import MockAIProvider, mock_provider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.settings import AISettings


def build_provider(settings: AISettings) -> MockAIProvider | OpenAICompatibleProvider:
    if settings.AI_MOCK_MODE or settings.AI_PROVIDER == "mock":
        return mock_provider
    return OpenAICompatibleProvider(
        api_key=settings.AI_API_KEY,
        base_url=settings.AI_API_BASE_URL,
        text_model=settings.AI_TEXT_MODEL,
        vision_model=settings.AI_VISION_MODEL,
        timeout_seconds=settings.AI_REQUEST_TIMEOUT_SECONDS,
        review_confidence_threshold=settings.AI_REVIEW_CONFIDENCE_THRESHOLD,
    )
