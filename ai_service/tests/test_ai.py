import pytest
from pydantic import ValidationError

from app.mock_provider import mock_provider
from app.settings import AISettings


def test_mock_image_classification_does_not_claim_to_analyze_pixels():
    result = mock_provider.classify_image("pothole.jpg")

    assert result.category == "other"
    assert result.confidence == 0
    assert result.is_mock is True
    assert result.is_relevant is False
    assert result.message is not None
    assert "not analyzed" in result.message


def test_real_ai_mode_requires_api_key():
    with pytest.raises(ValidationError, match="AI_API_KEY is required"):
        AISettings(AI_MOCK_MODE=False, AI_PROVIDER="openai_compatible", AI_API_KEY="")


def test_real_ai_mode_accepts_openai_compatible_configuration():
    settings = AISettings(
        AI_MOCK_MODE=False,
        AI_PROVIDER="openai_compatible",
        AI_API_KEY="sk-test",
    )
    assert settings.AI_PROVIDER == "openai_compatible"
