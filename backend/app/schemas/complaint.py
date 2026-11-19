"""
CivicLens — Complaint Schemas
Comprehensive request & response definitions for civic issues.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

from app.models.complaint import ComplaintPriority, ComplaintStatus, MediaType, VerificationAction
from app.schemas.auth import UserBrief
from app.schemas.department import CategoryResponse, DepartmentResponse


class MediaItem(BaseModel):
    id: str
    media_type: MediaType = MediaType.IMAGE
    media_url: str
    thumbnail_url: str | None = None
    file_name: str | None = None
    is_resolution_proof: bool = False
    evidence_stage: str | None = None
    uploaded_at: datetime | None = None

    class Config:
        from_attributes = True


class MediaMetadata(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_size: int = Field(ge=0, le=10 * 1024 * 1024)
    mime_type: str = Field(min_length=1, max_length=100)


class ResolutionEvidence(BaseModel):
    media_url: str
    stage: Literal["before", "after"]
    caption: str | None = Field(default=None, max_length=500)


class CommentItem(BaseModel):
    id: str
    comment: str
    is_internal: bool = False
    author_id: str
    author_name: str | None = None
    author_role: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class StatusHistoryItem(BaseModel):
    id: str
    old_status: str | None = None
    new_status: str
    changed_by_id: str | None = None
    changed_by_name: str | None = None
    notes: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class VerificationItem(BaseModel):
    id: str
    action: VerificationAction
    feedback: str | None = None
    rating: int | None = None
    verified_by_id: str
    verified_by_name: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ComplaintCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    description: str = Field(min_length=10, max_length=5000)
    category_id: str
    priority: ComplaintPriority = ComplaintPriority.MEDIUM
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    address: str | None = Field(default=None, max_length=500)
    landmark: str | None = Field(default=None, max_length=255)
    state: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    locality: str | None = Field(default=None, max_length=150)
    sub_district: str | None = Field(default=None, max_length=150)
    block: str | None = Field(default=None, max_length=150)
    gram_panchayat: str | None = Field(default=None, max_length=150)
    ward: str | None = Field(default=None, max_length=100)
    pincode: str | None = Field(default=None, pattern=r"^\d{6}$")
    language: str = Field(default="en", min_length=2, max_length=10)
    media_urls: list[str] = Field(default_factory=list)
    media_metadata: list[MediaMetadata] = Field(default_factory=list)
    voice_description_url: str | None = None
    resolution_notes: str | None = None
    client_temp_id: str | None = None  # For offline sync reconciliation


class ComplaintUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=255)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    priority: ComplaintPriority | None = None
    category_id: str | None = None
    address: str | None = None
    landmark: str | None = None


class StatusUpdate(BaseModel):
    status: ComplaintStatus
    notes: str | None = Field(default=None, max_length=1000)
    resolution_media_urls: list[str] = Field(default_factory=list)
    resolution_evidence: list[ResolutionEvidence] = Field(default_factory=list, max_length=10)


class ReopenRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class AssignmentUpdate(BaseModel):
    department_id: str | None = None
    staff_id: str | None = None
    notes: str | None = Field(default=None, max_length=1000)


class VerificationRequest(BaseModel):
    action: VerificationAction
    feedback: str | None = Field(default=None, max_length=2000)
    rating: int | None = Field(default=None, ge=1, le=5)


class ModerationReviewRequest(BaseModel):
    action: Literal["approve", "reject", "request_information", "confirmed_spam", "not_spam", "escalated"]
    reason: str = Field(min_length=5, max_length=2000)


class CommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=3000)
    is_internal: bool = False


class ComplaintResponse(BaseModel):
    id: str
    public_id: str
    title: str
    description: str
    category_id: str
    category: CategoryResponse | None = None
    priority: ComplaintPriority
    status: ComplaintStatus
    latitude: float | None = None
    longitude: float | None = None
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

    created_by: str
    creator: UserBrief | None = None

    assigned_department_id: str | None = None
    assigned_department: DepartmentResponse | None = None

    assigned_staff_id: str | None = None
    assigned_staff: UserBrief | None = None

    ai_category: str | None = None
    ai_confidence: float | None = None
    ai_is_mock: bool = False
    requires_human_review: bool = False
    ai_outcome: str = "human_review"
    ai_reason: str | None = None
    ai_model_version: str | None = None
    ai_verified_at: datetime | None = None
    ai_verification: dict = Field(default_factory=dict)

    duplicate_group_id: str | None = None
    duplicate_score: float | None = None

    voice_description_url: str | None = None
    resolution_notes: str | None = None

    media: list[MediaItem] = Field(default_factory=list)
    comments: list[CommentItem] = Field(default_factory=list)
    status_history: list[StatusHistoryItem] = Field(default_factory=list)
    verifications: list[VerificationItem] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    resolution_deadline: datetime | None = None
    resolution_submitted_at: datetime | None = None
    is_overdue: bool = False
    escalation_level: int = 0

    class Config:
        from_attributes = True


class ComplaintListItem(BaseModel):
    id: str
    public_id: str
    title: str
    category_name: str | None = None
    category_slug: str | None = None
    category_icon: str | None = None
    priority: ComplaintPriority
    status: ComplaintStatus
    address: str | None = None
    state: str | None = None
    district: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime
    updated_at: datetime
    creator_name: str | None = None
    assigned_department_name: str | None = None
    assigned_staff_name: str | None = None
    media_count: int = 0
    thumbnail_url: str | None = None
    requires_human_review: bool = False
    ai_is_mock: bool = False
    ai_outcome: str = "human_review"
    resolution_deadline: datetime | None = None
    is_overdue: bool = False
    escalation_level: int = 0

    class Config:
        from_attributes = True


class ComplaintFilters(BaseModel):
    status: ComplaintStatus | None = None
    priority: ComplaintPriority | None = None
    category_id: str | None = None
    department_id: str | None = None
    assigned_staff_id: str | None = None
    created_by: str | None = None
    state: str | None = None
    district: str | None = None
    search: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    page: int = 1
    per_page: int = 20


class DuplicateCandidate(BaseModel):
    id: str
    public_id: str
    title: str
    status: str
    category_name: str | None = None
    similarity_score: float
    distance_meters: float | None = None
    created_at: datetime
