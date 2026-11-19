"""User directory and administrator-controlled staff provisioning."""

from __future__ import annotations

from typing import Any

from pymongo.errors import DuplicateKeyError

from app.core import hash_password
from app.core.mongo import model_to_doc, utc_now
from app.exceptions import ConflictError, ValidationError
from app.models.user import User
from app.schemas.auth import CreateStaffRequest, UserBrief
from app.services.audit_service import AuditService


class UserService:
    def __init__(self, db: Any):
        self.db = db

    async def list_staff_by_department(self, department_id: str | None = None) -> list[UserBrief]:
        # Assignment targets are deliberately limited to field staff. Officers and
        # administrators can be returned by other directory views, never this one.
        query = {"is_active": True, "deleted_at": None, "is_suspended": {"$ne": True}, "roles": "field_staff"}
        if department_id:
            query["department_id"] = department_id
        docs = await self.db.users.find(query).sort("full_name", 1).to_list(length=500)
        return [await self._brief(User.model_validate(doc)) for doc in docs]

    async def get_user_brief(self, user_id: str) -> UserBrief | None:
        doc = await self.db.users.find_one({"_id": user_id, "deleted_at": None})
        return await self._brief(User.model_validate(doc)) if doc else None

    async def create_staff_account(self, req: CreateStaffRequest, *, actor_id: str, ip_address: str | None = None, user_agent: str | None = None) -> UserBrief:
        if req.role in {"officer", "field_staff"} and req.department_id is None:
            raise ValidationError("department_id is required for officers and field staff")
        if req.department_id and not await self.db.departments.find_one({"_id": req.department_id, "is_active": True}):
            raise ValidationError("Department not found")
        now = utc_now()
        user = User(
            email=str(req.email).lower(), full_name=req.full_name.strip(), phone=req.phone,
            password_hash=hash_password(req.password), roles=[req.role], department_id=req.department_id,
            is_active=True, is_verified=False, identity_verified=False, identity_provider=None,
            created_at=now, updated_at=now,
        )
        try:
            await self.db.users.insert_one(model_to_doc(user))
        except DuplicateKeyError as exc:
            raise ConflictError("A user with this email address already exists") from exc
        await AuditService(self.db).record(
            action="user.staff.create", resource_type="user", resource_id=user.id, actor_id=actor_id,
            details={"role": req.role, "department_id": req.department_id}, ip_address=ip_address, user_agent=user_agent,
        )
        return await self._brief(user)

    async def _brief(self, user: User) -> UserBrief:
        department = await self.db.departments.find_one({"_id": user.department_id}) if user.department_id else None
        return UserBrief(
            id=user.id, email=user.email, full_name=user.full_name, phone=user.phone, avatar_url=user.avatar_url,
            roles=user.roles, department_id=user.department_id, department_name=department.get("name") if department else None,
            city=user.city,
            is_active=user.is_active, is_verified=user.is_verified,
            email_verified=user.email_verified, mobile_verified=user.mobile_verified, identity_verified=user.identity_verified,
        )
