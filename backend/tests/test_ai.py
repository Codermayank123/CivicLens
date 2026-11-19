"""
CivicLens — AI Auto-Triage Tests
"""

import pytest
from httpx import AsyncClient

from app.exceptions import AIServiceError
from app.services.ai_client import AIClient


@pytest.mark.asyncio
async def test_ai_client_uses_service_route_and_form_contract(monkeypatch):
    request = {}

    class MockResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"category": "pothole", "confidence": 0.9, "urgency": "high"}

    class MockAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, url, data):
            request["url"] = url
            request["data"] = data
            return MockResponse()

    monkeypatch.setattr("app.services.ai_client.httpx.AsyncClient", MockAsyncClient)
    result = await AIClient().classify_text("Pothole on the road")

    assert request == {
        "url": "http://localhost:8001/classify-text",
        "data": {"text": "Pothole on the road"},
    }
    assert result["is_relevant"] is True


@pytest.mark.asyncio
async def test_ai_client_fails_closed_when_production_service_is_unavailable(monkeypatch):
    class MockResponse:
        status_code = 503

    class MockAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def post(self, url, data):
            return MockResponse()

    import app.services.ai_client as ai_client_module

    monkeypatch.setattr(ai_client_module.httpx, "AsyncClient", MockAsyncClient)
    monkeypatch.setattr(ai_client_module.settings, "APP_ENV", "production")

    with pytest.raises(AIServiceError):
        await AIClient().classify_text("Pothole on the road")


@pytest.mark.asyncio
async def test_ai_suggestion(client: AsyncClient):
    payload = {"text": "Hazardous live wire hanging from broken streetlight near school."}
    res = await client.post("/api/v1/ai/suggest", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "category" in data["data"]
    assert "urgency" in data["data"]
    assert data["data"]["urgency"] in ["high", "medium", "low"]
