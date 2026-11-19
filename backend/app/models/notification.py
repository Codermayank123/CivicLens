"""MongoDB notification document."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field, model_validator


class NotificationType(str, enum.Enum):
    COMPLAINT_SUBMITTED = "complaint_submitted"
    COMPLAINT_ASSIGNED = "complaint_assigned"
    STATUS_CHANGED = "status_changed"
    COMPLAINT_RESOLVED = "complaint_resolved"
    COMPLAINT_REOPENED = "complaint_reopened"
    VERIFICATION_REQUIRED = "verification_required"
    COMPLAINT_REJECTED = "complaint_rejected"
    DEADLINE_REMINDER = "deadline_reminder"
    ESCALATION = "escalation"
    SYSTEM = "system"


class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    type: NotificationType
    title: str
    message: str
    complaint_id: str | None = None
    is_read: bool = False
    read_at: datetime | None = None
    data: dict | None = None
    dedupe_key: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="before")
    @classmethod
    def map_mongo_id(cls, value: Any) -> Any:
        if isinstance(value, dict) and "_id" in value and "id" not in value:
            value = dict(value)
            value["id"] = str(value.pop("_id"))
        return value
