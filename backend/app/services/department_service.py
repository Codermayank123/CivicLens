"""Department and complaint taxonomy queries backed by MongoDB."""

from __future__ import annotations

from typing import Any

from app.schemas.department import CategoryResponse, DepartmentResponse


class DepartmentService:
    def __init__(self, db: Any):
        self.db = db

    async def list_departments(self) -> list[DepartmentResponse]:
        departments = await self.db.departments.find({"is_active": True}).sort("name", 1).to_list(length=200)
        results = []
        for department in departments:
            member_count = await self.db.users.count_documents({"department_id": department["_id"], "is_active": True, "deleted_at": None})
            results.append(DepartmentResponse(
                id=str(department["_id"]), name=department["name"], code=department["code"],
                description=department.get("description"), contact_email=department.get("contact_email"),
                contact_phone=department.get("contact_phone"), head_user_id=department.get("head_user_id"),
                is_active=department.get("is_active", True), member_count=member_count,
                created_at=department.get("created_at"),
            ))
        return results

    async def list_categories(self) -> list[CategoryResponse]:
        categories = await self.db.complaint_categories.find({"is_active": True}).sort([("display_order", 1), ("name", 1)]).to_list(length=200)
        department_ids = {item.get("department_id") for item in categories if item.get("department_id")}
        departments = await self.db.departments.find({"_id": {"$in": list(department_ids)}}).to_list(length=200) if department_ids else []
        names = {str(item["_id"]): item["name"] for item in departments}
        return [CategoryResponse(
            id=str(item["_id"]), name=item["name"], slug=item["slug"], description=item.get("description"),
            icon=item.get("icon"), color=item.get("color"), department_id=item.get("department_id"),
            department_name=names.get(str(item.get("department_id"))), parent_id=item.get("parent_id"), is_active=item.get("is_active", True),
            display_order=item.get("display_order", 0),
        ) for item in categories]
