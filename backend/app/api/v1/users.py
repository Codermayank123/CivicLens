"""
CivicLens — Users & Staff Endpoints
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.core.rate_limit import limiter
from app.dependencies import get_current_user, get_db, require_roles
from app.exceptions import ForbiddenError
from app.models.user import User
from app.schemas.auth import CreateStaffRequest, NotificationPreferencesUpdate, UserBrief
from app.schemas.common import ApiResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch("/me/notification-preferences", response_model=ApiResponse[dict[str, bool]])
async def update_notification_preferences(
    req: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[dict[str, bool]]:
    update = {key: value for key, value in req.model_dump(exclude_none=True).items()}
    if update:
        await db.users.update_one({"_id": current_user.id}, {"$set": update})
    return ApiResponse(success=True, data={
        "email_notifications": update.get("email_notifications", current_user.email_notifications),
        "sms_notifications": update.get("sms_notifications", current_user.sms_notifications),
    })


@router.get("/staff", response_model=ApiResponse[list[UserBrief]])
async def list_staff(
    department_id: str | None = None,
    current_user: User = Depends(require_roles("admin", "officer", "department_head")),
    db: Any = Depends(get_db),
) -> ApiResponse[list[UserBrief]]:
    roles = set(current_user.roles)
    if "admin" not in roles:
        if current_user.department_id is None:
            return ApiResponse(success=True, data=[])
        if department_id is not None and department_id != current_user.department_id:
            raise ForbiddenError("Officers may only view staff in their own department")
        department_id = current_user.department_id

    service = UserService(db)
    items = await service.list_staff_by_department(department_id)
    return ApiResponse(success=True, data=items)


@router.post("/staff", response_model=ApiResponse[UserBrief])
@limiter.limit(f"{get_settings().RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def create_staff_account(
    req: CreateStaffRequest,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: Any = Depends(get_db),
) -> ApiResponse[UserBrief]:
    service = UserService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    created = await service.create_staff_account(
        req,
        actor_id=current_user.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return ApiResponse(success=True, data=created, message="Staff account created")
