"""
CivicLens — Notifications Endpoints
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, Header, Query, Request, WebSocket, WebSocketDisconnect

from app.core import decode_token
from app.core.notification_hub import notification_hub
from app.database import get_database
from app.dependencies import get_current_user, get_db, require_roles
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.notification import NotificationListResponse
from app.services.notification_service import NotificationService
from app.config import get_settings
from app.exceptions import ForbiddenError

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/webhooks/brevo", include_in_schema=False)
async def brevo_webhook(
    request: Request,
    x_civiclens_webhook_secret: str | None = Header(default=None),
    db: Any = Depends(get_db),
) -> dict[str, bool]:
    settings = get_settings()
    if not settings.BREVO_WEBHOOK_SECRET or x_civiclens_webhook_secret != settings.BREVO_WEBHOOK_SECRET:
        raise ForbiddenError("Webhook authentication failed")
    payload = await request.json()
    event = str(payload.get("event") or payload.get("type") or "").lower()
    provider_message_id = str(payload.get("message-id") or payload.get("messageId") or payload.get("message_id") or "")
    if provider_message_id:
        mapped_status = {
            "delivered": "delivered",
            "sent": "accepted",
            "opened": "opened",
            "click": "clicked",
            "clicked": "clicked",
            "hard_bounce": "failed",
            "soft_bounce": "failed",
            "blocked": "failed",
            "error": "failed",
            "invalid_email": "failed",
        }.get(event)
        if mapped_status:
            await db.notification_deliveries.update_one(
                {"provider_message_id": provider_message_id},
                {"$set": {"status": mapped_status, "provider_status": event, "provider_event_at": datetime.now(timezone.utc)}},
            )
    return {"accepted": True}


@router.websocket("/stream")
async def notification_stream(websocket: WebSocket) -> None:
    """Push persisted notification events to an authenticated browser session."""
    token = websocket.query_params.get("access_token")
    try:
        payload = decode_token(token or "")
        if payload.get("type") != "access" or not payload.get("sub"):
            raise ValueError("invalid websocket token")
        user = await get_database().users.find_one({"_id": str(payload["sub"]), "deleted_at": None})
        if not user:
            raise ValueError("unknown websocket user")
    except Exception:
        await websocket.close(code=4401)
        return

    user_id = str(payload["sub"])
    await notification_hub.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_hub.disconnect(user_id, websocket)
    except Exception:
        notification_hub.disconnect(user_id, websocket)


@router.get("", response_model=ApiResponse[NotificationListResponse])
async def get_notifications(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[NotificationListResponse]:
    service = NotificationService(db)
    res = await service.get_user_notifications(current_user.id, limit=limit)
    return ApiResponse(success=True, data=res)


@router.post("/mark-read", response_model=ApiResponse[bool])
async def mark_notifications_read(
    notification_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[bool]:
    service = NotificationService(db)
    await service.mark_as_read(current_user.id, notification_id)
    return ApiResponse(success=True, data=True, message="Marked as read")


@router.get("/admin/delivery-summary", response_model=ApiResponse[dict[str, Any]])
async def delivery_summary(
    current_user: User = Depends(require_roles("admin")),
    db: Any = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    return ApiResponse(success=True, data=await NotificationService(db).admin_delivery_summary())
