"""
CivicLens — Complaints Endpoints
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user, get_db, require_roles
from app.exceptions import NotFoundError
from app.models.complaint import ComplaintPriority, ComplaintStatus
from app.models.user import User
from app.schemas.common import ApiResponse, PaginationMeta
from app.schemas.complaint import (
    AssignmentUpdate,
    CommentCreate,
    CommentItem,
    ComplaintCreate,
    ComplaintFilters,
    ComplaintListItem,
    ComplaintResponse,
    DuplicateCandidate,
    ModerationReviewRequest,
    StatusUpdate,
    VerificationRequest,
    ReopenRequest,
)
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post("", response_model=ApiResponse[ComplaintResponse])
async def create_complaint(
    data: ComplaintCreate,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[ComplaintResponse]:
    service = ComplaintService(db)
    complaint = await service.create(current_user, data)
    return ApiResponse(
        success=True,
        data=complaint,
        message=f"Complaint #{complaint.public_id} submitted successfully",
    )


@router.get("", response_model=ApiResponse[list[ComplaintListItem]])
async def list_complaints(
    status: ComplaintStatus | None = None,
    priority: ComplaintPriority | None = None,
    category_id: str | None = None,
    department_id: str | None = None,
    assigned_staff_id: str | None = None,
    created_by: str | None = None,
    state: str | None = None,
    district: str | None = None,
    search: str | None = None,
    current_user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: Any = Depends(get_db),
) -> ApiResponse[list[ComplaintListItem]]:
    filters = ComplaintFilters(
        status=status,
        priority=priority,
        category_id=category_id,
        department_id=department_id,
        assigned_staff_id=assigned_staff_id,
        created_by=created_by,
        state=state,
        district=district,
        search=search,
        page=page,
        per_page=per_page,
    )
    service = ComplaintService(db)
    items, total = await service.list_complaints(filters, current_user)

    meta = PaginationMeta(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )

    return ApiResponse(success=True, data=items, meta=meta)


@router.get("/my", response_model=ApiResponse[list[ComplaintListItem]])
async def get_my_complaints(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[list[ComplaintListItem]]:
    filters = ComplaintFilters(
        created_by=current_user.id,
        page=page,
        per_page=per_page,
    )
    service = ComplaintService(db)
    items, total = await service.list_complaints(filters, current_user)

    meta = PaginationMeta(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )
    return ApiResponse(success=True, data=items, meta=meta)


@router.get("/assigned-to-me", response_model=ApiResponse[list[ComplaintListItem]])
async def get_assigned_to_me(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[list[ComplaintListItem]]:
    filters = ComplaintFilters(
        assigned_staff_id=current_user.id,
        page=page,
        per_page=per_page,
    )
    service = ComplaintService(db)
    items, total = await service.list_complaints(filters, current_user)

    meta = PaginationMeta(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )
    return ApiResponse(success=True, data=items, meta=meta)


@router.get("/ai-review-queue", response_model=ApiResponse[list[ComplaintResponse]])
async def get_ai_review_queue(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_roles("admin", "officer", "department_head")),
    db: Any = Depends(get_db),
) -> ApiResponse[list[ComplaintResponse]]:
    items, total = await ComplaintService(db).list_ai_review_queue(current_user, page, per_page)
    return ApiResponse(success=True, data=items, meta=PaginationMeta(page=page, per_page=per_page, total=total, total_pages=(total + per_page - 1) // per_page if total else 0))


@router.post("/duplicates/check", response_model=ApiResponse[list[DuplicateCandidate]])
async def check_duplicates(
    title: str,
    description: str,
    category_id: str,
    latitude: float | None = None,
    longitude: float | None = None,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[list[DuplicateCandidate]]:
    service = ComplaintService(db)
    candidates = await service.check_potential_duplicates(
        title=title,
        description=description,
        category_id=category_id,
        latitude=latitude,
        longitude=longitude,
    )
    return ApiResponse(success=True, data=candidates)


@router.get("/nearby", response_model=ApiResponse[list[ComplaintListItem]])
async def nearby_complaints(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=2.0, gt=0, le=25),
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[list[ComplaintListItem]]:
    items = await ComplaintService(db).nearby_complaints(latitude, longitude, radius_km)
    return ApiResponse(success=True, data=items)


@router.get("/{id_or_public_id}", response_model=ApiResponse[ComplaintResponse])
async def get_complaint(
    id_or_public_id: str,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[ComplaintResponse]:
    service = ComplaintService(db)
    try:
        complaint = await service.get_by_id_for_user(id_or_public_id, current_user)
    except NotFoundError:
        complaint = await service.get_by_public_id_for_user(id_or_public_id, current_user)

    return ApiResponse(success=True, data=complaint)


@router.post("/{complaint_id}/support", response_model=ApiResponse[dict[str, Any]])
async def support_complaint(
    complaint_id: str,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[dict[str, Any]]:
    result = await ComplaintService(db).support_complaint(complaint_id, current_user)
    return ApiResponse(success=True, data=result, message="Neighbourhood support recorded")


@router.patch("/{complaint_id}/status", response_model=ApiResponse[ComplaintResponse])
async def update_status(
    complaint_id: str,
    data: StatusUpdate,
    current_user: User = Depends(require_roles("admin", "officer", "department_head", "field_staff")),
    db: Any = Depends(get_db),
) -> ApiResponse[ComplaintResponse]:
    service = ComplaintService(db)
    complaint = await service.update_status(complaint_id, current_user, data)
    return ApiResponse(success=True, data=complaint, message="Complaint status updated")


@router.patch("/{complaint_id}/assign", response_model=ApiResponse[ComplaintResponse])
async def assign_complaint(
    complaint_id: str,
    data: AssignmentUpdate,
    current_user: User = Depends(require_roles("admin", "officer", "department_head")),
    db: Any = Depends(get_db),
) -> ApiResponse[ComplaintResponse]:
    service = ComplaintService(db)
    complaint = await service.assign(complaint_id, current_user, data)
    return ApiResponse(success=True, data=complaint, message="Complaint assignment updated")


@router.post("/{complaint_id}/verify", response_model=ApiResponse[ComplaintResponse])
async def verify_complaint(
    complaint_id: str,
    data: VerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[ComplaintResponse]:
    service = ComplaintService(db)
    complaint = await service.verify_resolution(complaint_id, current_user, data)
    return ApiResponse(success=True, data=complaint, message="Verification logged successfully")


@router.post("/{complaint_id}/reopen", response_model=ApiResponse[ComplaintResponse])
async def reopen_complaint(
    complaint_id: str,
    data: ReopenRequest,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[ComplaintResponse]:
    complaint = await ComplaintService(db).reopen(complaint_id, current_user, data)
    return ApiResponse(success=True, data=complaint, message="Complaint reopened for review")


@router.post("/{complaint_id}/ai-moderation/review", response_model=ApiResponse[ComplaintResponse])
async def review_ai_moderation(
    complaint_id: str,
    data: ModerationReviewRequest,
    current_user: User = Depends(require_roles("admin", "officer", "department_head")),
    db: Any = Depends(get_db),
) -> ApiResponse[ComplaintResponse]:
    complaint = await ComplaintService(db).review_ai_moderation(complaint_id, current_user, data)
    return ApiResponse(success=True, data=complaint, message="AI moderation review recorded")


@router.post("/{complaint_id}/comments", response_model=ApiResponse[CommentItem])
async def add_comment(
    complaint_id: str,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Any = Depends(get_db),
) -> ApiResponse[CommentItem]:
    service = ComplaintService(db)
    comment = await service.add_comment(complaint_id, current_user, data)
    return ApiResponse(success=True, data=comment, message="Comment added")
