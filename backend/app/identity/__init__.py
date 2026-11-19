"""Modular identity verification integrations."""

from app.identity.registry import build_identity_provider, get_identity_provider

__all__ = ["build_identity_provider", "get_identity_provider"]
