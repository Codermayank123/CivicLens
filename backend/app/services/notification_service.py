"""In-app notification service with optional email delivery."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.config import get_settings
from app.core.notification_hub import notification_hub
from app.core.mongo import model_to_doc
from app.models.notification import Notification, NotificationType
from app.schemas.notification import NotificationItem, NotificationListResponse
from app.services.email_service import get_email_service
from app.services.sms_service import send_sms
from app.email.base import EmailAttachment
from app.services.storage_service import storage_service


class NotificationService:
    def __init__(self, db: Any):
        self.db = db

    async def create_notification(
        self, user_id: str, title: str, message: str, notification_type: str = "status_update",
        complaint_id: str | None = None, data: dict[str, Any] | None = None,
    ) -> Notification:
        type_map = {
            "status_update": NotificationType.STATUS_CHANGED,
            "assignment": NotificationType.COMPLAINT_ASSIGNED,
            "alert": NotificationType.SYSTEM,
            "mention": NotificationType.SYSTEM,
            "complaint_submitted": NotificationType.COMPLAINT_SUBMITTED,
            "complaint_resolved": NotificationType.COMPLAINT_RESOLVED,
            "complaint_reopened": NotificationType.COMPLAINT_REOPENED,
            "verification_required": NotificationType.VERIFICATION_REQUIRED,
            "complaint_rejected": NotificationType.COMPLAINT_REJECTED,
            "deadline_reminder": NotificationType.DEADLINE_REMINDER,
            "escalation": NotificationType.ESCALATION,
        }
        dedupe_key = None
        if complaint_id:
            dedupe_key = f"{user_id}:{complaint_id}:{notification_type}:{title}:{message}"
            existing = await self.db.notifications.find_one({"dedupe_key": dedupe_key})
            if existing:
                return Notification.model_validate(existing)
        notification = Notification(
            user_id=user_id, title=title, message=message,
            type=type_map.get(notification_type, NotificationType.SYSTEM), complaint_id=complaint_id, data=data, dedupe_key=dedupe_key,
        )
        await self.db.notifications.insert_one(model_to_doc(notification))
        await self.db.notification_deliveries.insert_one({"_id": f"{notification.id}:in_app", "notification_id": notification.id, "channel": "in_app", "status": "delivered", "created_at": notification.created_at})
        await notification_hub.publish(user_id, notification.model_dump(mode="json"))
        user = await self.db.users.find_one({"_id": user_id, "deleted_at": None}, {"email": 1, "phone": 1, "full_name": 1, "email_notifications": 1, "sms_notifications": 1})
        if user and user.get("email_notifications", True):
            delivery_id = f"{notification.id}:email"
            existing = await self.db.notification_deliveries.find_one({"_id": delivery_id})
            if not existing:
                delivery = {"_id": delivery_id, "notification_id": notification.id, "channel": "email", "status": "pending", "created_at": notification.created_at}
                await self.db.notification_deliveries.insert_one(delivery)
                try:
                    if complaint_id:
                        complaint = await self.db.complaints.find_one({"_id": complaint_id})
                        department = await self.db.departments.find_one({"_id": complaint.get("assigned_department_id")}) if complaint and complaint.get("assigned_department_id") else None
                        attachments: list[EmailAttachment] = []
                        if data and data.get("resolution"):
                            media_docs = await self.db.complaint_media.find({"complaint_id": complaint_id, "is_resolution_evidence": True}).sort("created_at", 1).to_list(length=10)
                            total_size = 0
                            for media in media_docs:
                                content = await storage_service.read_file_url(media.get("file_url", ""))
                                if content is None:
                                    continue
                                total_size += len(content)
                                if total_size > get_settings().MAX_RESOLUTION_EMAIL_ATTACHMENT_BYTES:
                                    attachments = []
                                    break
                                attachments.append(EmailAttachment(filename=media.get("file_name", "evidence.jpg"), content=content, content_type=media.get("mime_type", "image/jpeg")))
                        provider_id = await get_email_service().send_complaint_update(
                            to=user["email"],
                            name=user.get("full_name"),
                            public_id=(complaint or {}).get("public_id", str(complaint_id)),
                            status=(complaint or {}).get("status", "updated"),
                            remarks=(data or {}).get("remarks") or message,
                            updated_at=str((complaint or {}).get("updated_at") or notification.created_at),
                            department=(department or {}).get("name"),
                            tracking_url=f"{get_settings().FRONTEND_PUBLIC_URL.rstrip('/')}/complaints/{complaint_id}",
                            attachments=tuple(attachments),
                        )
                    else:
                        provider_id = await get_email_service().send(to=user["email"], subject=f"{get_settings().APP_NAME}: {title}", text_body=message)
                    await self.db.notification_deliveries.update_one({"_id": delivery_id}, {"$set": {"status": "accepted", "provider_status": "accepted", "provider_message_id": provider_id, "accepted_at": datetime.now(timezone.utc)}})
                except Exception as exc:
                    import structlog
                    structlog.get_logger().warning("notification.email_delivery_failed", user_id=user_id, error=type(exc).__name__)
                    await self.db.notification_deliveries.update_one({"_id": delivery_id}, {"$set": {"status": "failed", "error": type(exc).__name__, "failed_at": datetime.now(timezone.utc)}})
        if user and user.get("phone") and user.get("sms_notifications", True):
            delivery_id = f"{notification.id}:sms"
            if not await self.db.notification_deliveries.find_one({"_id": delivery_id}):
                status, error = await send_sms(user["phone"], message)
                await self.db.notification_deliveries.insert_one({"_id": delivery_id, "notification_id": notification.id, "channel": "sms", "status": status, "error": error, "created_at": notification.created_at})
        return notification

    async def admin_delivery_summary(self, limit: int = 5000) -> dict[str, Any]:
        docs = await self.db.notification_deliveries.find({}).sort("created_at", -1).limit(limit).to_list(length=limit)
        summary: dict[str, Any] = {"total": len(docs), "by_channel": {}, "by_status": {}, "recent_failures": []}
        for doc in docs:
            summary["by_channel"][doc.get("channel", "unknown")] = summary["by_channel"].get(doc.get("channel", "unknown"), 0) + 1
            summary["by_status"][doc.get("status", "unknown")] = summary["by_status"].get(doc.get("status", "unknown"), 0) + 1
            if doc.get("status") == "failed" and len(summary["recent_failures"]) < 20:
                summary["recent_failures"].append({"notification_id": doc.get("notification_id"), "channel": doc.get("channel"), "error": doc.get("error")})
        return summary

    async def get_user_notifications(self, user_id: str, limit: int = 50) -> NotificationListResponse:
        docs = await self.db.notifications.find({"user_id": user_id}).sort("created_at", -1).limit(limit).to_list(length=limit)
        unread_count = await self.db.notifications.count_documents({"user_id": user_id, "is_read": False})
        items = [NotificationItem(
            id=str(doc["_id"]), title=doc["title"], message=doc["message"],
            notification_type=doc.get("type", "system"), complaint_id=doc.get("complaint_id"),
            is_read=doc.get("is_read", False), created_at=doc["created_at"], data=doc.get("data"),
        ) for doc in docs]
        return NotificationListResponse(notifications=items, unread_count=unread_count)

    async def mark_as_read(self, user_id: str, notification_id: str | None = None) -> None:
        query = {"user_id": user_id}
        if notification_id:
            query["_id"] = notification_id
        await self.db.notifications.update_many(query, {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc)}})
