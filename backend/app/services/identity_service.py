"""Identity-provider orchestration with minimal-retention MongoDB sessions."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.config import get_settings
from app.core.mongo import as_utc, model_to_doc, utc_now
from app.exceptions import ForbiddenError, IdentityVerificationUnavailableError, ValidationError
from app.identity.registry import build_identity_provider
from app.identity.types import SessionCompleteResult
from app.models.identity import IdentitySessionStatus, IdentityVerificationSession
from app.models.user import User
from app.services.audit_service import AuditService


class IdentityService:
    SESSION_TTL = timedelta(minutes=30)

    def __init__(self, db: Any) -> None:
        self.db = db
        self.settings = get_settings()
        self.provider = build_identity_provider(self.settings)

    def public_status(self) -> dict:
        caps = self.provider.capabilities()
        return {
            "provider": self.provider.name,
            "citizen_registration_enabled": self.settings.citizen_registration_enabled,
            "supports_verification_sessions": caps.supports_verification_sessions,
            "collects_otp_on_server": caps.collects_otp_on_server,
            "collects_aadhaar_on_server": caps.collects_aadhaar_on_server,
            "is_sandbox": caps.is_sandbox,
            "is_production_ready": caps.is_production_ready,
            "consent_version": self.settings.IDENTITY_CONSENT_VERSION,
        }

    async def start_session(self, user: User, *, consent_accepted: bool, consent_version: str, ip_address: str | None, user_agent: str | None) -> dict:
        if "citizen" not in user.roles:
            raise ForbiddenError("Identity verification sessions are available only for citizen accounts")
        if not consent_accepted:
            raise ValidationError("Consent is required to start identity verification")
        if consent_version != self.settings.IDENTITY_CONSENT_VERSION:
            raise ValidationError("Consent version is outdated; refresh and accept the latest terms")
        caps = self.provider.capabilities()
        if not caps.supports_verification_sessions:
            raise IdentityVerificationUnavailableError()
        if user.identity_verified:
            raise ValidationError("Account is already identity-verified")
        now = utc_now()
        session = IdentityVerificationSession(
            user_id=user.id, provider=self.provider.name, status=IdentitySessionStatus.PENDING,
            consent_version=consent_version, consented_at=now, expires_at=now + self.SESSION_TTL,
        )
        result = await self.provider.start_session(user_id=user.id, consent_version=consent_version, session_id=session.id)
        session.status = IdentitySessionStatus.AWAITING_USER_ACTION if result.status == "awaiting_user_action" else IdentitySessionStatus.PENDING
        session.client_metadata = {"user_action": result.user_action, "official_endpoints": result.official_endpoints}
        await self.db.identity_verification_sessions.insert_one(model_to_doc(session))
        await AuditService(self.db).record(
            action="identity.session.start", resource_type="identity_session", resource_id=session.id, actor_id=user.id,
            details={"provider": self.provider.name, "consent_version": consent_version, "status": session.status.value},
            ip_address=ip_address, user_agent=user_agent,
        )
        return {"session_id": session.id, "status": session.status.value, "message": result.message, "expires_at": session.expires_at.isoformat(), "user_action": result.user_action, "official_endpoints": result.official_endpoints}

    async def complete_session(self, user: User, session_id: str, payload: dict, *, ip_address: str | None, user_agent: str | None) -> dict:
        session_doc = await self.db.identity_verification_sessions.find_one({"_id": session_id, "user_id": user.id})
        if not session_doc:
            raise ForbiddenError("Identity verification session not found")
        session = IdentityVerificationSession.model_validate(session_doc)
        if (as_utc(session.expires_at) or utc_now()) <= utc_now():
            await self.db.identity_verification_sessions.update_one({"_id": session.id}, {"$set": {"status": IdentitySessionStatus.EXPIRED.value, "updated_at": utc_now()}})
            raise ValidationError("Identity verification session has expired")
        if session.status not in {IdentitySessionStatus.PENDING, IdentitySessionStatus.AWAITING_USER_ACTION}:
            raise ValidationError("Identity verification session is no longer active")
        if any(key in payload for key in {"otp", "aadhaar", "aadhaar_number"}):
            raise ValidationError("Do not send OTP or Aadhaar numbers to CivicLens. Use the authorized provider flow.")
        now = utc_now()
        claim = await self.db.identity_verification_sessions.update_one(
            {
                "_id": session.id,
                "user_id": user.id,
                "status": {"$in": [IdentitySessionStatus.PENDING.value, IdentitySessionStatus.AWAITING_USER_ACTION.value]},
                "expires_at": {"$gt": now},
            },
            {"$set": {"status": IdentitySessionStatus.VERIFYING.value, "updated_at": now}},
        )
        if getattr(claim, "modified_count", 0) != 1:
            raise ValidationError("Identity verification session is no longer active")
        try:
            result = await self.provider.complete_session(user_id=user.id, session_id=session.id, payload=payload)
        except Exception:
            result = SessionCompleteResult(
                success=False,
                status="failed",
                message="Identity provider verification failed. Your account remains unverified.",
                failure_code="PROVIDER_ERROR",
            )
        update = {"status": IdentitySessionStatus.COMPLETED.value if result.success and result.verified else IdentitySessionStatus.FAILED.value, "updated_at": now, "client_metadata": None}
        if result.success and result.verified:
            update.update({"completed_at": now})
            await self.db.users.update_one({"_id": user.id, "identity_verified": {"$ne": True}}, {"$set": {"is_verified": True, "identity_verified": True, "identity_provider": self.provider.name, "updated_at": now}})
        else:
            update.update({"failure_code": result.failure_code, "failure_message": result.message})
        await self.db.identity_verification_sessions.update_one({"_id": session.id, "user_id": user.id, "status": IdentitySessionStatus.VERIFYING.value}, {"$set": update})
        await AuditService(self.db).record(
            action="identity.session.completed" if result.success and result.verified else "identity.session.failed",
            resource_type="identity_session", resource_id=session.id, actor_id=user.id,
            details={"provider": self.provider.name, "verified": bool(result.success and result.verified)},
            ip_address=ip_address, user_agent=user_agent,
        )
        return {"session_id": session.id, "status": update["status"], "verified": bool(result.success and result.verified), "message": result.message}

    async def get_session(self, user: User, session_id: str) -> dict:
        doc = await self.db.identity_verification_sessions.find_one({"_id": session_id, "user_id": user.id})
        if not doc:
            raise ForbiddenError("Identity verification session not found")
        session = IdentityVerificationSession.model_validate(doc)
        return {"session_id": session.id, "status": session.status.value, "provider": session.provider, "expires_at": session.expires_at.isoformat(), "completed_at": session.completed_at.isoformat() if session.completed_at else None, "failure_code": session.failure_code, "failure_message": session.failure_message}
