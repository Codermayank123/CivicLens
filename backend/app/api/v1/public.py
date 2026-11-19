"""Privacy-safe public information used by the unauthenticated landing page."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.dependencies import get_db
from app.schemas.common import ApiResponse
from app.schemas.analytics import ImpactTrackerResponse, StateMetric
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/public", tags=["Public platform information"])


@router.get("/platform", response_model=ApiResponse[dict[str, Any]])
async def platform_summary(db: Any = Depends(get_db)) -> ApiResponse[dict[str, Any]]:
    """Return aggregate, non-identifying indicators and resolved cases."""
    active_query = {"deleted_at": None}
    resolved_query = {"deleted_at": None, "status": {"$in": ["resolved", "closed"]}}
    total = await db.complaints.count_documents(active_query)
    resolved = await db.complaints.count_documents(resolved_query)
    departments = await db.departments.count_documents({"is_active": True})
    recent_docs = await db.complaints.find(resolved_query).sort("updated_at", -1).limit(4).to_list(length=4)
    recent = []
    for item in recent_docs:
        category = await db.complaint_categories.find_one({"_id": item.get("category_id")})
        recent.append({"public_id": item["public_id"], "title": item["title"], "category_name": category.get("name") if category else "Civic issue", "status": item["status"], "updated_at": item["updated_at"]})
    return ApiResponse(success=True, data={"total_complaints": total, "resolved_complaints": resolved, "active_departments": departments, "resolution_rate": round((resolved / total) * 100) if total else 0, "recent_resolutions": recent})


@router.get("/heatmap", response_model=ApiResponse[list[dict[str, Any]]])
async def public_heatmap(db: Any = Depends(get_db)) -> ApiResponse[list[dict[str, Any]]]:
    points = await AnalyticsService(db).get_public_heatmap()
    return ApiResponse(success=True, data=[point.model_dump() for point in points])


@router.get("/accountability", response_model=ApiResponse[list[dict[str, Any]]])
async def public_accountability(db: Any = Depends(get_db)) -> ApiResponse[list[dict[str, Any]]]:
    return ApiResponse(success=True, data=await AnalyticsService(db).get_accountability())


@router.get("/impact", response_model=ApiResponse[ImpactTrackerResponse])
async def public_impact(db: Any = Depends(get_db)) -> ApiResponse[ImpactTrackerResponse]:
    return ApiResponse(success=True, data=await AnalyticsService(db).get_impact_tracker())


@router.get("/india", response_model=ApiResponse[list[StateMetric]])
async def public_india(db: Any = Depends(get_db)) -> ApiResponse[list[StateMetric]]:
    return ApiResponse(success=True, data=await AnalyticsService(db).get_state_metrics())
