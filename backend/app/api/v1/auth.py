"""
CivicLens — Auth Endpoints
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Request, Response

from app.dependencies import get_current_user, get_db
from app.core.rate_limit import limiter
from app.config import get_settings
from app.exceptions import TokenInvalidError
from app.models.user import User
from app.schemas.auth import (
    CompleteRegistrationRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegistrationOtpRequest,
    VerifyRegistrationOtpRequest,
    RequestPhoneOtpRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserBrief,
    VerifyEmailRequest,
    VerifyPhoneOtpRequest,
)
from app.schemas.common import ApiResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register/request-otp", response_model=ApiResponse[dict[str, int | str]])
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def request_registration_otp(
    req: RegistrationOtpRequest,
    request: Request,
    db: Any = Depends(get_db),
) -> ApiResponse[dict[str, int | str]]:
    result = await AuthService(db).request_registration_otp(req)
    return ApiResponse(success=True, data=result, message="Verification code sent")


@router.post("/register/verify-otp", response_model=ApiResponse[dict[str, int | str]])
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def verify_registration_otp(
    req: VerifyRegistrationOtpRequest,
    request: Request,
    db: Any = Depends(get_db),
) -> ApiResponse[dict[str, int | str]]:
    result = await AuthService(db).verify_registration_otp(req)
    return ApiResponse(success=True, data=result, message="Verification successful")


@router.post("/register", response_model=ApiResponse[TokenResponse], response_model_exclude_none=True)
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def register(
    req: CompleteRegistrationRequest,
    request: Request,
    response: Response,
    db: Any = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    service = AuthService(db)
    token_response = await service.register(req)
    _set_refresh_cookie(response, token_response.refresh_token)
    public_response = token_response.model_copy(update={"refresh_token": None})
    return ApiResponse(success=True, data=public_response, message="Account created after OTP verification")


@router.post("/login", response_model=ApiResponse[TokenResponse], response_model_exclude_none=True)
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Any = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    user_agent = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None

    service = AuthService(db)
    token_response = await service.login(req, user_agent, ip_address)

    _set_refresh_cookie(response, token_response.refresh_token)

    public_response = token_response.model_copy(update={"refresh_token": None})
    return ApiResponse(success=True, data=public_response, message="Login successful")


@router.post("/refresh", response_model=ApiResponse[TokenResponse], response_model_exclude_none=True)
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def refresh_token(
    req: RefreshTokenRequest,
    request: Request,
    response: Response,
    db: Any = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    token_str = req.refresh_token or request.cookies.get("refresh_token")
    if not token_str:
        raise TokenInvalidError("Missing refresh token")
    service = AuthService(db)
    token_response = await service.refresh_tokens(token_str)

    _set_refresh_cookie(response, token_response.refresh_token)

    public_response = token_response.model_copy(update={"refresh_token": None})
    return ApiResponse(success=True, data=public_response, message="Token refreshed successfully")


@router.post("/logout", response_model=ApiResponse[bool])
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def logout(
    request: Request,
    response: Response,
    db: Any = Depends(get_db),
) -> ApiResponse[bool]:
    token_str = request.cookies.get("refresh_token")
    service = AuthService(db)
    await service.logout(token_str)
    response.delete_cookie(
        "refresh_token",
        path="/api/v1/auth",
        secure=get_settings().is_production,
        httponly=True,
        samesite="lax",
    )
    return ApiResponse(success=True, data=True, message="Logged out successfully")


@router.post("/forgot-password", response_model=ApiResponse[bool])
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    db: Any = Depends(get_db),
) -> ApiResponse[bool]:
    service = AuthService(db)
    await service.request_password_reset(req)
    return ApiResponse(
        success=True,
        data=True,
        message="If an account exists for that email, password reset instructions were sent.",
    )


@router.post("/reset-password", response_model=ApiResponse[bool])
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def reset_password(
    req: ResetPasswordRequest,
    request: Request,
    db: Any = Depends(get_db),
) -> ApiResponse[bool]:
    service = AuthService(db)
    await service.reset_password(req)
    return ApiResponse(success=True, data=True, message="Password updated successfully")


@router.post("/verify-email", response_model=ApiResponse[bool])
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def verify_email(
    req: VerifyEmailRequest,
    request: Request,
    db: Any = Depends(get_db),
) -> ApiResponse[bool]:
    await AuthService(db).verify_email(req.token)
    return ApiResponse(success=True, data=True, message="Email address verified")


@router.post("/phone/request-otp", response_model=ApiResponse[dict[str, int | str]])
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def request_phone_otp(
    req: RequestPhoneOtpRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[dict[str, int | str]]:
    result = await AuthService(db).request_phone_otp(current_user, req)
    return ApiResponse(success=True, data=result, message="Verification code sent")


@router.post("/phone/verify-otp", response_model=ApiResponse[bool])
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def verify_phone_otp(
    req: VerifyPhoneOtpRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[bool]:
    await AuthService(db).verify_phone_otp(current_user, req)
    return ApiResponse(success=True, data=True, message="Phone number verified")


@router.get("/me", response_model=ApiResponse[UserBrief])
async def get_me(
    current_user: User = Depends(get_current_user),
) -> ApiResponse[UserBrief]:
    user_brief = UserBrief(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        avatar_url=current_user.avatar_url,
        roles=current_user.roles,
        department_id=current_user.department_id,
        department_name=None,
        city=current_user.city,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        email_verified=current_user.email_verified,
        mobile_verified=current_user.mobile_verified,
        identity_verified=current_user.identity_verified,
        email_notifications=current_user.email_notifications,
        sms_notifications=current_user.sms_notifications,
    )
    return ApiResponse(success=True, data=user_brief)


def _set_refresh_cookie(response: Response, token: str | None) -> None:
    if token:
        response.set_cookie(
            key="refresh_token",
            value=token,
            httponly=True,
            secure=get_settings().is_production,
            samesite="lax",
            path="/api/v1/auth",
            max_age=get_settings().JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        )
