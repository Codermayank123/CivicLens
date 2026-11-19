"""Dependency health checks for readiness probes."""

from __future__ import annotations

import asyncio
import redis.asyncio as aioredis

from app.config import Settings, get_settings
from app.database import get_database
from app.services.storage_backends import LocalStorageBackend, S3StorageBackend
from app.services.storage_service import UPLOAD_DIR


async def check_database() -> bool:
    """Check MongoDB connectivity."""
    try:
        db = get_database()
        res = await db.command("ping")
        return bool(res and res.get("ok"))
    except Exception:
        return False


async def check_redis(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    if not cfg.REDIS_ENABLED:
        return True
    try:
        client = aioredis.from_url(cfg.REDIS_URL, socket_connect_timeout=2)
        try:
            return bool(await client.ping())
        finally:
            await client.aclose()
    except Exception:
        return False


async def check_storage(settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    backend = (
        S3StorageBackend(cfg)
        if cfg.STORAGE_BACKEND == "s3"
        else LocalStorageBackend(UPLOAD_DIR)
    )
    return await backend.check_connection()


async def readiness_report(settings: Settings | None = None) -> dict[str, bool]:
    cfg = settings or get_settings()
    db_ok, redis_ok, storage_ok = await asyncio.gather(
        check_database(),
        check_redis(cfg),
        check_storage(cfg),
    )
    return {
        "database": db_ok,
        "redis": redis_ok,
        "storage": storage_ok,
    }
