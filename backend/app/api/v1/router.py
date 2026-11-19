"""
CivicLens — API v1 Master Router
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.complaints import router as complaints_router
from app.api.v1.departments import departments_router, categories_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.users import router as users_router
from app.api.v1.media import router as media_router
from app.api.v1.ai import router as ai_router
from app.api.v1.identity import router as identity_router
from app.api.v1.public import router as public_router
from app.api.v1.rewards import router as rewards_router
from app.api.v1.locations import router as locations_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router)
api_v1_router.include_router(complaints_router)
api_v1_router.include_router(departments_router)
api_v1_router.include_router(categories_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(media_router)
api_v1_router.include_router(ai_router)
api_v1_router.include_router(identity_router)
api_v1_router.include_router(public_router)
api_v1_router.include_router(rewards_router)
api_v1_router.include_router(locations_router)

__all__ = ["api_v1_router"]
