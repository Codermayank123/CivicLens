"""
CivicLens — Analytics Endpoints
"""

from __future__ import annotations

from typing import Any
from datetime import datetime
from fastapi import APIRouter, Depends, Query

from app.dependencies import get_db, require_roles
from app.models.user import User
from app.schemas.analytics import HeatmapPoint, ImpactTrackerResponse, OverviewStats, StateMetric
from app.schemas.common import ApiResponse
from app.services.analytics_service import AnalyticsService
from app.services.deadline_service import list_escalations

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=ApiResponse[OverviewStats])
async def get_overview_stats(
    current_user: User = Depends(require_roles("admin")),
    db: Any = Depends(get_db),
) -> ApiResponse[OverviewStats]:
    service = AnalyticsService(db)
    stats = await service.get_overview_stats()
    return ApiResponse(success=True, data=stats)


@router.get("/heatmap", response_model=ApiResponse[list[HeatmapPoint]])
async def get_heatmap(
    current_user: User = Depends(require_roles("admin")),
    db: Any = Depends(get_db),
) -> ApiResponse[list[HeatmapPoint]]:
    service = AnalyticsService(db)
    points = await service.get_heatmap_points()
    return ApiResponse(success=True, data=points)


@router.get("/accountability", response_model=ApiResponse[list[dict]])
async def get_accountability(
    current_user: User = Depends(require_roles("admin", "officer", "department_head")),
    db: Any = Depends(get_db),
) -> ApiResponse[list[dict]]:
    return ApiResponse(success=True, data=await AnalyticsService(db).get_accountability())


@router.get("/impact", response_model=ApiResponse[ImpactTrackerResponse])
async def get_impact_tracker(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    department_id: str | None = None,
    category_id: str | None = None,
    status: str | None = None,
    current_user: User = Depends(require_roles("admin", "officer", "department_head")),
    db: Any = Depends(get_db),
) -> ApiResponse[ImpactTrackerResponse]:
    if "admin" not in current_user.roles:
        if department_id and department_id != current_user.department_id:
            from app.exceptions import ForbiddenError
            raise ForbiddenError("Department users may only view their own impact metrics")
        department_id = current_user.department_id
    data = await AnalyticsService(db).get_impact_tracker(start_date=start_date, end_date=end_date, department_id=department_id, category_id=category_id, status=status)
    return ApiResponse(success=True, data=data)


@router.get("/india", response_model=ApiResponse[list[StateMetric]])
async def get_india_state_metrics(
    state: str | None = Query(default=None, max_length=100),
    current_user: User = Depends(require_roles("admin", "officer", "department_head")),
    db: Any = Depends(get_db),
) -> ApiResponse[list[StateMetric]]:
    service = AnalyticsService(db)
    docs = await db.complaints.find({"deleted_at": None}).to_list(length=50000)
    if "admin" not in current_user.roles:
        docs = [doc for doc in docs if doc.get("assigned_department_id") == current_user.department_id]
    return ApiResponse(success=True, data=await service.get_state_metrics(docs=docs, state=state))


@router.get("/escalations", response_model=ApiResponse[list[dict]])
async def get_escalations(
    status: str | None = Query(default=None, max_length=50),
    current_user: User = Depends(require_roles("admin", "officer", "department_head")),
    db: Any = Depends(get_db),
) -> ApiResponse[list[dict]]:
    rows = await list_escalations(db, status=status)
    if "admin" not in current_user.roles:
        complaint_ids = {item["_id"] for item in await db.complaints.find({"assigned_department_id": current_user.department_id}).to_list(length=50000)}
        rows = [row for row in rows if row.get("complaint_id") in complaint_ids]
    return ApiResponse(success=True, data=rows)


@router.get("/ai-review-summary", response_model=ApiResponse[dict[str, int]])
async def get_ai_review_summary(
    current_user: User = Depends(require_roles("admin", "officer", "department_head")),
    db: Any = Depends(get_db),
) -> ApiResponse[dict[str, int]]:
    query: dict[str, Any] = {"deleted_at": None}
    if "admin" not in current_user.roles:
        query["assigned_department_id"] = current_user.department_id
    docs = await db.complaints.find(query).to_list(length=50000)
    return ApiResponse(success=True, data={
        "accepted": sum(doc.get("ai_outcome") == "accepted" for doc in docs),
        "human_review": sum(doc.get("ai_outcome") == "human_review" for doc in docs),
        "rejected": sum(doc.get("ai_outcome") == "rejected" for doc in docs),
        "pending_human_review": sum(bool(doc.get("requires_human_review")) for doc in docs),
    })
