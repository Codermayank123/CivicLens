"""MongoDB-backed authentication and session lifecycle."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any

import structlog
import httpx
from pymongo.errors import DuplicateKeyError

from app.config import get_settings
from app.core import (
    create_access_token,
    create_refresh_token,
    create_verification_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.mongo import as_utc, model_to_doc, utc_now
from app.exceptions import AccountSuspendedError, AuthenticationFailedError, ConflictError, ProviderUnavailableError, RateLimitError, TokenInvalidError, ValidationError
from app.identity.registry import build_identity_provider
from app.models.user import User
from app.schemas.auth import (
    CompleteRegistrationRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    RegistrationOtpRequest,
    RequestPhoneOtpRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserBrief,
    VerifyPhoneOtpRequest,
    VerifyRegistrationOtpRequest,
)
from app.services.sms_service import send_otp, verify_otp
from app.services.sms_service import send_sms
from app.services.email_service import get_email_service

logger = structlog.get_logger()


class AuthService:
    def __init__(self, db: Any):
        self.db = db

    async def request_registration_otp(self, req: RegistrationOtpRequest) -> dict[str, int | str]:
        """Create a short-lived registration session and deliver one OTP.

        The pending document stores only a password hash, session-token hash and
        OTP hash. The account is not created until the session is verified.
        """
        settings = get_settings()
        email = str(req.email).lower()
        existing = await self.db.users.find_one({"email": email, "deleted_at": None})
        if existing:
            raise ConflictError("A user with this email address already exists")
        if req.verification_method == "sms":
            if not req.phone or not req.phone.startswith("+91"):
                raise ValidationError("SMS verification requires an Indian +91 mobile number")
        if req.phone:
            existing_phone = await self.db.users.find_one({"phone": req.phone, "deleted_at": None})
            if existing_phone:
                raise ConflictError("A user with this phone number already exists")

        now = utc_now()
        recent = await self.db.registration_verifications.find_one(
            {"email": email, "status": "pending", "created_at": {"$gte": now - timedelta(minutes=settings.OTP_RATE_LIMIT_WINDOW_MINUTES)}},
            sort=[("created_at", -1)],
        )
        if recent:
            resend_at = as_utc(recent.get("resend_available_at"))
            if resend_at and resend_at > now:
                raise RateLimitError("Please wait before requesting another verification code")
            if int(recent.get("request_count", 1)) >= settings.OTP_MAX_REQUESTS_PER_WINDOW:
                raise RateLimitError("Too many verification requests; please try again later")

        session_id = secrets.token_urlsafe(24)
        session_token = secrets.token_urlsafe(32)
        code = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = now + timedelta(minutes=settings.OTP_SESSION_TTL_MINUTES)
        session_doc: dict[str, Any] = {
            "_id": session_id,
            "session_token_hash": hashlib.sha256(session_token.encode()).hexdigest(),
            "email": email,
            "full_name": req.full_name.strip(),
            "phone": req.phone,
            "verification_method": req.verification_method,
            "password_hash": hash_password(req.password),
            "code_hash": hashlib.sha256(f"{settings.JWT_SECRET_KEY}:{session_id}:{code}".encode()).hexdigest() if req.verification_method == "email" else None,
            "provider_verification_id": None,
            "attempts": 0,
            "request_count": int(recent.get("request_count", 0)) + 1 if recent else 1,
            "status": "pending",
            "created_at": now,
            "expires_at": expires_at,
            "resend_available_at": now + timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS),
        }
        if recent:
            await self.db.registration_verifications.update_one(
                {"_id": recent["_id"], "status": "pending"},
                {"$set": {"status": "superseded", "superseded_at": now}},
            )
        if req.verification_method == "email":
            try:
                await get_email_service().send_otp(to=email, code=code, expires_in_minutes=settings.OTP_SESSION_TTL_MINUTES)
            except Exception as exc:
                logger.warning("registration.email_otp_delivery_failed", error=type(exc).__name__)
                session_doc["status"] = "delivery_failed"
                await self.db.registration_verifications.insert_one(session_doc)
                raise ProviderUnavailableError("Email OTP delivery was not accepted by the configured provider") from exc
        else:
            try:
                status, verification_id, error = await send_otp(req.phone or "", code)
            except (ValueError, httpx.HTTPError) as exc:
                raise ProviderUnavailableError("SMS OTP provider is unavailable") from exc
            if status != "sent" or not verification_id:
                session_doc["status"] = "delivery_failed"
                await self.db.registration_verifications.insert_one(session_doc)
                raise ProviderUnavailableError(error or "SMS OTP delivery was not accepted by the configured provider")
            session_doc["provider_verification_id"] = verification_id
        await self.db.registration_verifications.insert_one(session_doc)
        return {
            "verification_session_id": session_id,
            "verification_token": session_token,
            "expires_in": settings.OTP_SESSION_TTL_MINUTES * 60,
            "resend_after": settings.OTP_RESEND_COOLDOWN_SECONDS,
            "verification_method": req.verification_method,
        }

    async def verify_registration_otp(self, req: VerifyRegistrationOtpRequest) -> dict[str, int | str]:
        settings = get_settings()
        token_hash = hashlib.sha256(req.verification_token.encode()).hexdigest()
        now = utc_now()
        session = await self.db.registration_verifications.find_one({"_id": req.verification_session_id, "session_token_hash": token_hash})
        if not session or session.get("status") != "pending" or (as_utc(session.get("expires_at")) or now) <= now:
            raise TokenInvalidError("The verification session is invalid or expired")
        attempts = int(session.get("attempts", 0))
        if attempts >= settings.OTP_MAX_ATTEMPTS:
            raise RateLimitError("Too many invalid verification attempts")

        valid = False
        error: str | None = None
        if session.get("verification_method") == "email":
            expected = hashlib.sha256(f"{settings.JWT_SECRET_KEY}:{req.verification_session_id}:{req.code}".encode()).hexdigest()
            valid = hmac.compare_digest(expected, str(session.get("code_hash", "")))
        else:
            provider_id = str(session.get("provider_verification_id") or "")
            valid, error = await verify_otp(str(session.get("phone") or ""), provider_id, req.code)
        if not valid:
            next_attempts = attempts + 1
            update: dict[str, Any] = {"$inc": {"attempts": 1}}
            if next_attempts >= settings.OTP_MAX_ATTEMPTS:
                update["$set"] = {"status": "exhausted"}
            await self.db.registration_verifications.update_one({"_id": req.verification_session_id, "status": "pending"}, update)
            if error:
                raise ProviderUnavailableError(error)
            raise TokenInvalidError("The verification code is invalid or expired")

        result = await self.db.registration_verifications.update_one(
            {"_id": req.verification_session_id, "session_token_hash": token_hash, "status": "pending"},
            {"$set": {"status": "verified", "verified_at": now}},
        )
        if not getattr(result, "modified_count", 0):
            raise TokenInvalidError("The verification session has already been used")
        return {"status": "verified", "expires_in": max(0, int(((as_utc(session.get("expires_at")) or now) - now).total_seconds()))}

    async def register(self, req: RegisterRequest | CompleteRegistrationRequest) -> TokenResponse:
        settings = get_settings()
        token_hash = hashlib.sha256(req.verification_token.encode()).hexdigest()
        session = await self.db.registration_verifications.find_one({"_id": req.verification_session_id, "session_token_hash": token_hash, "status": "verified"})
        if not session or (as_utc(session.get("expires_at")) or utc_now()) <= utc_now():
            raise TokenInvalidError("The verification session is invalid, expired, or already used")
        consumed = await self.db.registration_verifications.update_one(
            {"_id": req.verification_session_id, "session_token_hash": token_hash, "status": "verified"},
            {"$set": {"status": "consumed", "consumed_at": utc_now()}},
        )
        if not getattr(consumed, "modified_count", 0):
            raise TokenInvalidError("The verification session has already been used")
        now = utc_now()
        user = User(
            email=session["email"],
            full_name=session["full_name"],
            phone=session.get("phone"),
            password_hash=session["password_hash"],
            roles=["citizen"],
            is_active=True,
            is_verified=True,
            email_verified=session.get("verification_method") == "email",
            mobile_verified=session.get("verification_method") == "sms",
            identity_verified=True,
            identity_provider=f"otp_{session.get('verification_method')}",
            created_at=now,
            updated_at=now,
        )
        try:
            await self.db.users.insert_one(model_to_doc(user))
        except DuplicateKeyError as exc:
            raise ConflictError("A user with this email address already exists") from exc
        await get_email_service().send_welcome(to=user.email, name=user.full_name)
        return await self._generate_token_response(user, None, None)

    async def verify_email(self, token: str) -> bool:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user_doc = await self.db.users.find_one({"verification_token": token_hash, "deleted_at": None})
        user = User.model_validate(user_doc) if user_doc else None
        if not user or not user.verification_token_expires or (as_utc(user.verification_token_expires) or utc_now()) < utc_now():
            raise TokenInvalidError("Email verification link is invalid or has expired")
        await self.db.users.update_one(
            {"_id": user.id},
            {"$set": {"email_verified": True, "updated_at": utc_now()}, "$unset": {"verification_token": "", "verification_token_expires": ""}},
        )
        return True

    async def request_phone_otp(self, user: User, request: RequestPhoneOtpRequest) -> dict[str, int | str]:
        """Create and deliver a one-time phone verification code.

        The code is never persisted or logged in plaintext. A request may not
        silently replace the phone number already attached to the account.
        """
        phone = user.phone
        if not phone:
            raise ValidationError("Add an international phone number before requesting verification")
        if request.phone and request.phone != phone:
            raise ValidationError("The requested phone number does not match this account")
        now = utc_now()
        cooldown_start = now - timedelta(seconds=get_settings().OTP_RESEND_COOLDOWN_SECONDS)
        recent = await self.db.otp_challenges.find_one({
            "user_id": user.id,
            "purpose": "phone_verification",
            "created_at": {"$gte": cooldown_start},
        })
        if recent:
            raise RateLimitError("Please wait before requesting another verification code")

        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge_id = secrets.token_urlsafe(24)
        digest = hashlib.sha256(f"{get_settings().JWT_SECRET_KEY}:{user.id}:{code}".encode()).hexdigest()
        expires_at = now + timedelta(minutes=get_settings().OTP_EXPIRY_MINUTES)
        await self.db.otp_challenges.insert_one({
            "_id": challenge_id,
            "user_id": user.id,
            "phone": phone,
            "purpose": "phone_verification",
            "code_hash": digest,
            "attempts": 0,
            "status": "pending",
            "created_at": now,
            "expires_at": expires_at,
        })
        delivery_status, delivery_error = await send_sms(
            phone,
            f"{get_settings().APP_NAME} verification code: {code}. It expires in {get_settings().OTP_EXPIRY_MINUTES} minutes.",
        )
        if delivery_status != "sent":
            await self.db.otp_challenges.update_one(
                {"_id": challenge_id},
                {"$set": {"status": "delivery_failed", "delivery_error": delivery_error}},
            )
            raise ProviderUnavailableError("SMS delivery was not accepted by the configured provider")
        return {"status": "sent", "expires_in": get_settings().OTP_EXPIRY_MINUTES * 60}

    async def verify_phone_otp(self, user: User, request: VerifyPhoneOtpRequest) -> bool:
        now = utc_now()
        challenge = await self.db.otp_challenges.find_one(
            {"user_id": user.id, "purpose": "phone_verification", "status": "pending", "expires_at": {"$gt": now}},
            sort=[("created_at", -1)],
        )
        if not challenge:
            raise TokenInvalidError("The phone verification code is invalid or expired")
        if int(challenge.get("attempts", 0)) >= get_settings().OTP_MAX_ATTEMPTS:
            raise RateLimitError("Too many invalid verification attempts")
        expected = hashlib.sha256(f"{get_settings().JWT_SECRET_KEY}:{user.id}:{request.code}".encode()).hexdigest()
        if not hmac.compare_digest(expected, str(challenge.get("code_hash", ""))):
            attempts = int(challenge.get("attempts", 0)) + 1
            update: dict[str, Any] = {"$inc": {"attempts": 1}}
            if attempts >= get_settings().OTP_MAX_ATTEMPTS:
                update.setdefault("$set", {})["status"] = "exhausted"
            await self.db.otp_challenges.update_one({"_id": challenge["_id"]}, update)
            raise TokenInvalidError("The phone verification code is invalid or expired")
        await self.db.otp_challenges.update_one(
            {"_id": challenge["_id"], "status": "pending"},
            {"$set": {"status": "consumed", "consumed_at": now}},
        )
        await self.db.users.update_one(
            {"_id": user.id},
            {"$set": {"mobile_verified": True, "updated_at": now}},
        )
        await get_email_service().send_security_alert(
            to=user.email,
            message="Your CivicLens mobile number was verified successfully. If you did not do this, contact support immediately.",
        )
        return True

    async def login(self, req: LoginRequest, user_agent: str | None = None, ip_address: str | None = None) -> TokenResponse:
        user_doc = await self.db.users.find_one({"email": str(req.email).lower(), "deleted_at": None})
        user = User.model_validate(user_doc) if user_doc else None
        if not user or not verify_password(req.password, user.password_hash):
            raise AuthenticationFailedError("Invalid email or password")
        if user.is_suspended:
            raise AccountSuspendedError(user.suspended_reason or "Account has been suspended")
        if not user.is_active:
            raise AuthenticationFailedError("Account has been deactivated")
        now = utc_now()
        await self.db.users.update_one({"_id": user.id}, {"$set": {"last_login_at": now, "updated_at": now}})
        user.last_login_at = now
        return await self._generate_token_response(user, user_agent, ip_address)

    async def refresh_tokens(self, refresh_token_str: str) -> TokenResponse:
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh" or not payload.get("sub"):
            raise TokenInvalidError("Invalid refresh token")
        token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
        stored = await self.db.refresh_tokens.find_one({"token_hash": token_hash, "user_id": payload["sub"], "revoked": False})
        expires_at = as_utc(stored.get("expires_at")) if stored else None
        if not stored or not expires_at or expires_at <= utc_now():
            raise TokenInvalidError("Refresh token has been revoked or is invalid")
        user_doc = await self.db.users.find_one({"_id": payload["sub"], "deleted_at": None})
        user = User.model_validate(user_doc) if user_doc else None
        if not user:
            raise TokenInvalidError("User account no longer exists")
        if user.is_suspended:
            raise AccountSuspendedError(user.suspended_reason or "Account has been suspended")
        if not user.is_active:
            raise AuthenticationFailedError("Account has been deactivated")
        await self.db.refresh_tokens.update_one({"_id": stored["_id"]}, {"$set": {"revoked": True, "revoked_at": utc_now()}})
        return await self._generate_token_response(user, None, None)

    async def request_password_reset(self, req: ForgotPasswordRequest) -> None:
        user_doc = await self.db.users.find_one({"email": str(req.email).lower(), "deleted_at": None})
        if not user_doc:
            return
        user = User.model_validate(user_doc)
        raw_token = create_verification_token()
        now = utc_now()
        await self.db.users.update_one(
            {"_id": user.id},
            {"$set": {"reset_token": hashlib.sha256(raw_token.encode()).hexdigest(), "reset_token_expires": now + timedelta(minutes=get_settings().PASSWORD_RESET_TOKEN_EXPIRE_MINUTES), "updated_at": now}},
        )
        reset_url = f"{get_settings().FRONTEND_PUBLIC_URL.rstrip('/')}/reset-password?token={raw_token}"
        await get_email_service().send_password_reset(
            to=user.email,
            reset_url=reset_url,
            expires_in_minutes=get_settings().PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
        )

    async def reset_password(self, req: ResetPasswordRequest) -> None:
        token_hash = hashlib.sha256(req.token.encode()).hexdigest()
        now = utc_now()
        user_doc = await self.db.users.find_one({"reset_token": token_hash, "deleted_at": None})
        user = User.model_validate(user_doc) if user_doc else None
        if not user or not user.reset_token_expires or (as_utc(user.reset_token_expires) or now) < now:
            raise TokenInvalidError("Password reset link is invalid or has expired")
        await self.db.users.update_one(
            {"_id": user.id},
            {"$set": {"password_hash": hash_password(req.new_password), "updated_at": now}, "$unset": {"reset_token": "", "reset_token_expires": ""}},
        )
        await get_email_service().send_security_alert(
            to=user.email,
            message="Your CivicLens password was changed successfully. If you did not request this change, contact support immediately.",
        )

    async def logout(self, refresh_token_str: str | None) -> None:
        if not refresh_token_str:
            return
        token_hash = hashlib.sha256(refresh_token_str.encode()).hexdigest()
        await self.db.refresh_tokens.update_one({"token_hash": token_hash}, {"$set": {"revoked": True, "revoked_at": utc_now()}})

    async def _generate_token_response(self, user: User, user_agent: str | None, ip_address: str | None) -> TokenResponse:
        access_token = create_access_token(user.id, user.roles)
        refresh_token, expires_at = create_refresh_token(user.id)
        await self.db.refresh_tokens.insert_one({
            "_id": create_verification_token(),
            "user_id": user.id,
            "token_hash": hashlib.sha256(refresh_token.encode()).hexdigest(),
            "expires_at": expires_at,
            "revoked": False,
            "created_at": utc_now(),
            "user_agent": user_agent,
            "ip_address": ip_address,
        })
        department_name = None
        if user.department_id:
            department = await self.db.departments.find_one({"_id": user.department_id})
            department_name = department.get("name") if department else None
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=get_settings().JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserBrief(
                id=user.id, email=user.email, full_name=user.full_name, phone=user.phone,
                avatar_url=user.avatar_url, roles=user.roles, department_id=user.department_id,
                department_name=department_name, city=user.city, is_active=user.is_active, is_verified=user.is_verified,
                email_verified=user.email_verified, mobile_verified=user.mobile_verified, identity_verified=user.identity_verified,
                email_notifications=user.email_notifications, sms_notifications=user.sms_notifications,
            ),
        )
