"""Append-only audit logging for security-sensitive actions."""

from __future__ import annotations

from typing import Any

from app.core.mongo import model_to_doc
from app.models.audit import AuditLog


class AuditService:
    def __init__(self, db: Any) -> None:
        self.db = db

    async def record(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        actor_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self.db.audit_logs.insert_one(model_to_doc(entry))
        return entry
