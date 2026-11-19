import base64

import pytest

from app.email.base import EmailAttachment, EmailMessage
from app.email.providers.brevo import BrevoEmailProvider
from app.services.sms_service import MessageCentralProvider


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        raise AssertionError("unexpected HTTP error")


class FakeAsyncClient:
    response = FakeResponse(201, {"messageId": "provider-message-id"})
    last_headers = None
    last_payload = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, headers, json):
        self.last_headers = headers
        self.last_payload = json
        return self.response


@pytest.mark.asyncio
async def test_brevo_payload_contains_branded_content_and_attachment(monkeypatch):
    client = FakeAsyncClient()
    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: client)
    provider = BrevoEmailProvider(api_key="test-key", sender_email="sender@example.com", sender_name="CivicLens")
    result = await provider.send(
        EmailMessage(
            to="citizen@example.com",
            subject="Resolution",
            text_body="The complaint was resolved.",
            html_body="<strong>Resolved</strong>",
            attachments=(EmailAttachment("after.jpg", b"image-bytes", "image/jpeg"),),
        )
    )
    assert result == "provider-message-id"
    assert client.last_headers["api-key"] == "test-key"
    assert client.last_payload["sender"]["name"] == "CivicLens"
    assert client.last_payload["attachment"][0]["content"] == base64.b64encode(b"image-bytes").decode()


@pytest.mark.asyncio
async def test_message_central_verifynow_contract(monkeypatch):
    provider = MessageCentralProvider(customer_id="customer", auth_token="token", base_url="https://cpaas.messagecentral.com")
    calls = []

    async def fake_request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        if path.endswith("/send"):
            return FakeResponse(200, {"data": {"verificationId": "verification-123"}})
        return FakeResponse(200, {"responseCode": 200, "data": {"verificationStatus": "VERIFICATION_COMPLETED"}})

    monkeypatch.setattr(provider, "_request", fake_request)
    status, verification_id, error = await provider.send_otp("+919876543210")
    assert (status, verification_id, error) == ("sent", "verification-123", None)
    valid, error = await provider.verify_otp("+919876543210", verification_id, "123456")
    assert valid is True
    assert error is None
    assert calls[0][0:2] == ("POST", "/verification/v3/send")
    assert calls[0][2]["params"]["countryCode"] == "91"
    assert calls[0][2]["params"]["mobileNumber"] == "9876543210"
    assert calls[1][0:2] == ("GET", "/verification/v3/validateOtp")


@pytest.mark.asyncio
async def test_message_central_provider_rejection_is_not_success(monkeypatch):
    provider = MessageCentralProvider(customer_id="customer", auth_token="token", base_url="https://cpaas.messagecentral.com")

    async def fake_request(method, path, **kwargs):
        return FakeResponse(503, {})

    monkeypatch.setattr(provider, "_request", fake_request)
    status, verification_id, error = await provider.send_otp("+919876543210")
    assert status == "failed"
    assert verification_id is None
    assert error
