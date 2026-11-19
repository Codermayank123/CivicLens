import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_settings_reject_development_defaults():
    with pytest.raises(ValidationError, match="Unsafe production configuration"):
        Settings(APP_ENV="production")


@pytest.mark.parametrize(
    ("identity_provider", "provider_settings", "expected_error"),
    [
        (
            "uidai_sandbox",
            {"UIDAI_AUA_CODE": "test-aua", "UIDAI_LICENSE_KEY": "test-license"},
            "UIDAI sandbox is not production-ready",
        ),
        (
            "uidai_offline_ekyc",
            {"UIDAI_OFFLINE_EKYC_CERT_PATH": "uidai-cert.pem"},
            "Offline e-KYC signature verification is not implemented",
        ),
    ],
)
def test_production_registration_rejects_unverified_identity_providers(
    identity_provider: str,
    provider_settings: dict[str, str],
    expected_error: str,
):
    with pytest.raises(ValidationError, match=expected_error):
        Settings(
            APP_ENV="production",
            CITIZEN_REGISTRATION_ENABLED=True,
            IDENTITY_PROVIDER=identity_provider,
            **provider_settings,
        )