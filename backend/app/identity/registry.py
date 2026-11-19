"""Resolve configured identity verification provider."""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from app.identity.base import IdentityProvider
from app.identity.providers.development import DevelopmentIdentityProvider
from app.identity.providers.disabled import DisabledIdentityProvider
from app.identity.providers.uidai_offline_ekyc import UidaiOfflineEkycIdentityProvider
from app.identity.providers.uidai_sandbox import UidaiSandboxIdentityProvider
from app.identity.types import IdentityProviderMode


def build_identity_provider(settings: Settings | None = None) -> IdentityProvider:
    cfg = settings or get_settings()
    mode = IdentityProviderMode(cfg.IDENTITY_PROVIDER)

    if mode == IdentityProviderMode.DISABLED:
        return DisabledIdentityProvider()
    if mode == IdentityProviderMode.DEVELOPMENT:
        return DevelopmentIdentityProvider()
    if mode == IdentityProviderMode.UIDAI_SANDBOX:
        return UidaiSandboxIdentityProvider(cfg)
    if mode == IdentityProviderMode.UIDAI_OFFLINE_EKYC:
        return UidaiOfflineEkycIdentityProvider(cfg)

    return DisabledIdentityProvider()


@lru_cache
def get_identity_provider() -> IdentityProvider:
    return build_identity_provider()
