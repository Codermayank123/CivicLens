from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.schemas.common import ApiResponse
from app.services.location_service import india_districts, india_states, india_sub_districts, reverse_geocode

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get("/reverse-geocode", response_model=ApiResponse[dict[str, Any]])
async def reverse_geocode_location(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
) -> ApiResponse[dict[str, Any]]:
    return ApiResponse(success=True, data=await reverse_geocode(latitude, longitude))


@router.get("/india/states", response_model=ApiResponse[list[dict[str, Any]]])
async def get_india_states() -> ApiResponse[list[dict[str, Any]]]:
    return ApiResponse(success=True, data=await india_states())


@router.get("/india/districts", response_model=ApiResponse[list[dict[str, Any]]])
async def get_india_districts(state: str = Query(..., min_length=2, max_length=100)) -> ApiResponse[list[dict[str, Any]]]:
    return ApiResponse(success=True, data=await india_districts(state))


@router.get("/india/sub-districts", response_model=ApiResponse[list[dict[str, str]]])
async def get_india_sub_districts(
    state: str = Query(..., min_length=2, max_length=100),
    district: str = Query(..., min_length=2, max_length=100),
) -> ApiResponse[list[dict[str, str]]]:
    return ApiResponse(success=True, data=await india_sub_districts(state, district))
