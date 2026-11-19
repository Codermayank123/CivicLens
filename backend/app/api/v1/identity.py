"""
CivicLens — Identity verification endpoints.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.core.rate_limit import limiter
from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.identity import (
    CompleteIdentitySessionRequest,
    IdentitySessionResponse,
    IdentityStatusResponse,
    StartIdentitySessionRequest,
)
from app.services.identity_service import IdentityService

router = APIRouter(prefix="/identity", tags=["Identity Verification"])


@router.get("/status", response_model=ApiResponse[IdentityStatusResponse])
@limiter.limit(f"{get_settings().RATE_LIMIT_PER_MINUTE}/minute")
async def get_identity_status(
    request: Request,
    db: Any = Depends(get_db),
) -> ApiResponse[IdentityStatusResponse]:
    service = IdentityService(db)
    return ApiResponse(success=True, data=IdentityStatusResponse(**service.public_status()))


@router.post("/sessions", response_model=ApiResponse[IdentitySessionResponse])
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def start_identity_session(
    req: StartIdentitySessionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[IdentitySessionResponse]:
    service = IdentityService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    data = await service.start_session(
        current_user,
        consent_accepted=req.consent_accepted,
        consent_version=req.consent_version,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return ApiResponse(success=True, data=IdentitySessionResponse(**data))


@router.post(
    "/sessions/{session_id}/complete",
    response_model=ApiResponse[IdentitySessionResponse],
)
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def complete_identity_session(
    session_id: str,
    req: CompleteIdentitySessionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[IdentitySessionResponse]:
    service = IdentityService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    payload = req.model_dump(exclude_none=True)
    payload["expected_full_name"] = current_user.full_name
    data = await service.complete_session(
        current_user,
        session_id,
        payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return ApiResponse(success=True, data=IdentitySessionResponse(**data))


@router.get("/sessions/{session_id}", response_model=ApiResponse[IdentitySessionResponse])
async def get_identity_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[IdentitySessionResponse]:
    service = IdentityService(db)
    data = await service.get_session(current_user, session_id)
    return ApiResponse(success=True, data=IdentitySessionResponse(**data))
