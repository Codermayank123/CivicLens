"""
CivicLens — Departments & Categories Endpoints
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends

from app.dependencies import get_db
from app.schemas.common import ApiResponse
from app.schemas.department import CategoryResponse, DepartmentResponse
from app.services.department_service import DepartmentService

departments_router = APIRouter(prefix="/departments", tags=["Departments"])
categories_router = APIRouter(prefix="/categories", tags=["Categories"])


@departments_router.get("", response_model=ApiResponse[list[DepartmentResponse]])
async def list_departments(
    db: Any = Depends(get_db),
) -> ApiResponse[list[DepartmentResponse]]:
    service = DepartmentService(db)
    items = await service.list_departments()
    return ApiResponse(success=True, data=items)


@categories_router.get("", response_model=ApiResponse[list[CategoryResponse]])
async def list_categories(
    db: Any = Depends(get_db),
) -> ApiResponse[list[CategoryResponse]]:
    service = DepartmentService(db)
    items = await service.list_categories()
    return ApiResponse(success=True, data=items)
