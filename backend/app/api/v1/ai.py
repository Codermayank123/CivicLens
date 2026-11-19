"""
CivicLens — AI Assist Endpoints
Provides real-time AI suggestions for citizens during complaint composition.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Body
from app.schemas.common import ApiResponse
from app.services.ai_client import ai_client

router = APIRouter(prefix="/ai", tags=["AI Assistance"])


@router.post("/suggest", response_model=ApiResponse[dict[str, Any]])
async def suggest_category_and_urgency(
    text: str = Body(..., embed=True),
) -> ApiResponse[dict[str, Any]]:
    result = await ai_client.classify_text(text)
    return ApiResponse(success=True, data=result)
