import json

import pytest

from app.providers.openai_compatible import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_openai_compatible_classify_text_parses_response(monkeypatch):
    provider = OpenAICompatibleProvider(
        api_key="test-key",
        base_url="https://api.example.com/v1",
        text_model="test-model",
        vision_model="test-model",
        timeout_seconds=5.0,
        review_confidence_threshold=0.5,
    )

    class MockResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "category": "pothole",
                                    "confidence": 0.91,
                                    "urgency": "medium",
                                    "suggested_priority": "medium",
                                    "is_relevant": True,
                                    "keywords": ["pothole", "road"],
                                }
                            )
                        }
                    }
                ]
            }

    class MockClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            assert headers["Authorization"] == "Bearer test-key"
            return MockResponse()

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", MockClient)
    result = await provider.classify_text("Large pothole damaging vehicles")
    assert result.category == "pothole"
    assert result.is_mock is False
    assert result.is_relevant is True
