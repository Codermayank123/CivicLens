"""
CivicLens — Celery Application

Background task processing for AI classification, notifications,
and offline sync reconciliation.
"""

from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "civiclens",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes hard limit
    task_default_queue="civiclens",
    task_routes={
        "app.tasks.ai_tasks.*": {"queue": "ai"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.sync_tasks.*": {"queue": "sync"},
    },
)

# Auto-discover tasks in the tasks package
celery_app.autodiscover_tasks(["app.tasks"])
