"""
CivicLens — Notification Schemas
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class NotificationItem(BaseModel):
    id: str
    title: str
    message: str
    notification_type: str  # status_update, assignment, mention, reminder, alert
    complaint_id: str | None = None
    is_read: bool = False
    created_at: datetime
    data: dict | None = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: list[NotificationItem] = Field(default_factory=list)
    unread_count: int = 0
