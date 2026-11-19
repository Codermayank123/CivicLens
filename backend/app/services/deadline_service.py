"""Complaint SLA deadlines, reminders, and human-reviewed escalations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import get_settings
from app.core.mongo import utc_now
from app.models.complaint import ComplaintPriority, ComplaintStatus
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService


DEFAULT_SLA_HOURS = {
    ComplaintPriority.LOW.value: 168,
    ComplaintPriority.MEDIUM.value: 72,
    ComplaintPriority.HIGH.value: 48,
    ComplaintPriority.CRITICAL.value: 24,
}

ACTIVE_STATUSES = {
    ComplaintStatus.SUBMITTED.value,
    ComplaintStatus.UNDER_REVIEW.value,
    ComplaintStatus.VERIFIED.value,
    ComplaintStatus.ASSIGNED.value,
    ComplaintStatus.IN_PROGRESS.value,
    ComplaintStatus.REOPENED.value,
    ComplaintStatus.CITIZEN_VERIFICATION_PENDING.value,
}


def calculate_deadline(created_at: datetime, priority: str, category: dict[str, Any] | None = None) -> datetime:
    """Calculate a deadline using category SLA when configured, otherwise priority SLA."""
    configured = (category or {}).get("sla_hours")
    try:
        hours = max(1, int(configured)) if configured is not None else DEFAULT_SLA_HOURS.get(priority, 72)
    except (TypeError, ValueError):
        hours = DEFAULT_SLA_HOURS.get(priority, 72)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at + timedelta(hours=hours)


async def _recipient_ids(db: Any, complaint: dict[str, Any]) -> list[str]:
    ids: set[str] = set()
    if complaint.get("assigned_staff_id"):
        ids.add(str(complaint["assigned_staff_id"]))
    department_id = complaint.get("assigned_department_id")
    if department_id:
        officers = await db.users.find({
            "department_id": department_id,
            "roles": {"$in": ["officer", "department_head"]},
            "is_active": True,
            "deleted_at": None,
        }).to_list(length=200)
        ids.update(str(item["_id"]) for item in officers)
    admins = await db.users.find({"roles": "admin", "is_active": True, "deleted_at": None}).to_list(length=200)
    ids.update(str(item["_id"]) for item in admins)
    return sorted(ids)


async def _notify_recipients(db: Any, ids: list[str], title: str, message: str, kind: str, complaint_id: str, data: dict[str, Any]) -> None:
    service = NotificationService(db)
    for user_id in ids:
        await service.create_notification(user_id, title, message, kind, complaint_id, data)


async def run_deadline_scan(db: Any) -> dict[str, int]:
    """Mark overdue work, send one daily reminder, and create escalation records.

    Escalation records are intentionally advisory: an authorized human still
    decides what administrative action, if any, should follow.
    """
    now = utc_now()
    settings = get_settings()
    reminder_cutoff = now + timedelta(hours=settings.DEADLINE_REMINDER_HOURS)
    docs = await db.complaints.find({
        "deleted_at": None,
        "status": {"$in": list(ACTIVE_STATUSES)},
        "resolution_deadline": {"$ne": None},
    }).to_list(length=10000)
    reminders = 0
    escalations = 0
    overdue = 0
    for complaint in docs:
        deadline = complaint.get("resolution_deadline")
        if not deadline:
            continue
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        recipients = await _recipient_ids(db, complaint)
        if deadline <= now:
            overdue += 1
            update: dict[str, Any] = {"is_overdue": True, "overdue_at": complaint.get("overdue_at") or now, "updated_at": now}
            last_escalated = complaint.get("last_escalated_at")
            if last_escalated and last_escalated.tzinfo is None:
                last_escalated = last_escalated.replace(tzinfo=timezone.utc)
            should_escalate = not last_escalated or last_escalated <= now - timedelta(hours=settings.ESCALATION_REPEAT_HOURS)
            if should_escalate:
                level = int(complaint.get("escalation_level", 0)) + 1
                update.update({"escalation_level": level, "last_escalated_at": now})
                escalation_id = f"escalation:{complaint['_id']}:{level}"
                existing = await db.complaint_escalations.find_one({"_id": escalation_id})
                if not existing:
                    await db.complaint_escalations.insert_one({
                        "_id": escalation_id,
                        "complaint_id": complaint["_id"],
                        "public_id": complaint.get("public_id"),
                        "level": level,
                        "status": "pending_human_action",
                        "reason": "Resolution deadline exceeded",
                        "created_at": now,
                        "notified_user_ids": recipients,
                    })
                    await _notify_recipients(
                        db,
                        recipients,
                        "Complaint escalated",
                        f"Complaint #{complaint.get('public_id')} has exceeded its resolution deadline and requires attention.",
                        "escalation",
                        complaint["_id"],
                        {"level": level, "deadline": deadline.isoformat()},
                    )
                    await AuditService(db).record(
                        action="complaint.escalated",
                        resource_type="complaint",
                        resource_id=complaint["_id"],
                        details={"level": level, "deadline": deadline.isoformat()},
                    )
                    escalations += 1
            await db.complaints.update_one({"_id": complaint["_id"]}, {"$set": update})
        elif deadline <= reminder_cutoff:
            last_reminder = complaint.get("last_deadline_reminder_at")
            if last_reminder and last_reminder.tzinfo is None:
                last_reminder = last_reminder.replace(tzinfo=timezone.utc)
            if not last_reminder or last_reminder <= now - timedelta(hours=12):
                await db.complaints.update_one({"_id": complaint["_id"]}, {"$set": {"last_deadline_reminder_at": now, "updated_at": now}})
                await _notify_recipients(
                    db,
                    recipients,
                    "Resolution deadline approaching",
                    f"Complaint #{complaint.get('public_id')} is due by {deadline.astimezone(timezone.utc).strftime('%d %b %Y %H:%M UTC')}.",
                    "deadline_reminder",
                    complaint["_id"],
                    {"deadline": deadline.isoformat()},
                )
                reminders += 1
    return {"scanned": len(docs), "overdue": overdue, "reminders": reminders, "escalations": escalations}


async def list_escalations(db: Any, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    return await db.complaint_escalations.find(query).sort("created_at", -1).limit(limit).to_list(length=limit)
