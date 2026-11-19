"""Authentication, role checks, and object-level authorization for MongoDB."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, Request

from app.core import decode_token
from app.database import get_db
from app.exceptions import AccountSuspendedError, ForbiddenError, InsufficientRoleError, TokenInvalidError
from app.models.user import User


async def get_current_user(request: Request, db: Any = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise TokenInvalidError("Missing or invalid Authorization header")
    payload = decode_token(auth_header[7:])
    if payload.get("type") != "access" or not payload.get("sub"):
        raise TokenInvalidError("Invalid token type")
    user_doc = await db.users.find_one({"_id": str(payload["sub"]), "deleted_at": None})
    user = User.model_validate(user_doc) if user_doc else None
    if not user:
        raise TokenInvalidError("User not found")
    if user.is_suspended:
        raise AccountSuspendedError()
    if not user.is_active:
        raise ForbiddenError("Account is deactivated")
    return user


def require_roles(*allowed_roles: str):
    async def _check_roles(current_user: User = Depends(get_current_user)) -> User:
        if "admin" not in current_user.roles and not set(current_user.roles).intersection(allowed_roles):
            raise InsufficientRoleError(
                f"Required roles: {', '.join(allowed_roles)}. Your roles: {', '.join(current_user.roles)}"
            )
        return current_user
    return _check_roles


def require_permission(resource: str, action: str):
    async def _check_permission(current_user: User = Depends(get_current_user), db: Any = Depends(get_db)) -> User:
        roles = await db.roles.find({"name": {"$in": current_user.roles}}).to_list(length=20)
        permissions = {permission for role in roles for permission in role.get("permissions", [])}
        if f"{resource}.{action}" not in permissions and "admin" not in current_user.roles:
            raise ForbiddenError(f"Missing permission: {resource}.{action}")
        return current_user
    return _check_permission


def check_resource_ownership(resource_owner_id: str, current_user: User, allow_roles: set[str] | None = None) -> None:
    if allow_roles and set(current_user.roles).intersection(allow_roles):
        return
    if resource_owner_id != current_user.id:
        raise ForbiddenError("You do not have access to this resource")
