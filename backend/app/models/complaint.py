"""
CivicLens — Complaint & Related Domain MongoDB Models

Core domain model with full lifecycle tracking:
categories, media, assignments, status history, comments, duplicates, verifications.
Uses GeoJSON Point for MongoDB 2dsphere geographic queries.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ComplaintStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CITIZEN_VERIFICATION_PENDING = "citizen_verification_pending"
    REOPENED = "reopened"
    CLOSED = "closed"


class ComplaintPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MediaType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"


class VerificationAction(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class SyncStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    SYNCED = "synced"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"


class Complaint(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    public_id: str
    title: str
    description: str

    category_id: str
    priority: ComplaintPriority = ComplaintPriority.MEDIUM
    status: ComplaintStatus = ComplaintStatus.SUBMITTED

    # Geographic location (GeoJSON Point: [longitude, latitude])
    latitude: float | None = None
    longitude: float | None = None
    location: dict[str, Any] | None = None
    address: str | None = None
    landmark: str | None = None
    state: str | None = None
    district: str | None = None
    city: str | None = None
    locality: str | None = None
    sub_district: str | None = None
    block: str | None = None
    gram_panchayat: str | None = None
    ward: str | None = None
    pincode: str | None = None
    original_language: str = "en"

    # Ownership and Assignment
    created_by: str
    assigned_department_id: str | None = None
    assigned_staff_id: str | None = None

    # AI Predictions & Metadata
    ai_category: str | None = None
    ai_confidence: float | None = None
    ai_is_mock: bool = False
    ai_verification: dict[str, Any] | None = None
    requires_human_review: bool = False
    ai_outcome: str = "human_review"  # accepted, human_review, rejected
    ai_reason: str | None = None
    ai_model_version: str | None = None
    ai_verified_at: datetime | None = None

    # Duplicate tracking & Community support
    duplicate_group_id: str | None = None
    duplicate_score: float | None = None
    supporters: list[str] = Field(default_factory=list)
    support_count: int = 0

    # Media & Voice
    voice_description_url: str | None = None
    resolution_notes: str | None = None
    resolution_deadline: datetime | None = None
    resolution_submitted_at: datetime | None = None
    is_overdue: bool = False
    escalation_level: int = 0
    last_deadline_reminder_at: datetime | None = None
    last_escalated_at: datetime | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    deleted_at: datetime | None = None

    @classmethod
    def make_geojson(cls, lat: float | None, lon: float | None) -> dict[str, Any] | None:
        if lat is not None and lon is not None:
            return {"type": "Point", "coordinates": [lon, lat]}
        return None


class ComplaintMedia(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    complaint_id: str
    media_type: MediaType
    file_url: str
    file_name: str
    file_size: int
    mime_type: str
    is_resolution_evidence: bool = False
    evidence_stage: str | None = None  # before, after, or supporting
    sha256: str | None = None
    caption: str | None = None
    uploaded_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ComplaintAssignment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    complaint_id: str
    department_id: str
    assigned_to: str | None = None
    assigned_by: str
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ComplaintStatusHistory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    complaint_id: str
    from_status: ComplaintStatus | None = None
    to_status: ComplaintStatus
    changed_by: str
    reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ComplaintComment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    complaint_id: str
    user_id: str
    content: str
    is_internal: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ComplaintVerification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    complaint_id: str
    verified_by: str
    action: VerificationAction
    reason: str | None = None
    rating: int | None = None
    evidence_url: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ComplaintDuplicate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    complaint_id: str
    duplicate_of_id: str
    similarity_score: float
    text_similarity: float = 0.0
    geo_distance_km: float = 0.0
    category_match: bool = False
    confirmed: bool | None = None
    reviewed_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SyncEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    complaint_id: str | None = None
    client_id: str
    status: SyncStatus = SyncStatus.PENDING
    payload_hash: str
    error_message: str | None = None
    attempts: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    synced_at: datetime | None = None
