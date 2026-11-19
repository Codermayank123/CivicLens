"""
CivicLens — Common API Schemas
Standard response envelope and pagination models.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class PaginationMeta(BaseModel):
    page: int = Field(ge=1, default=1)
    per_page: int = Field(ge=1, le=100, default=20)
    total: int = Field(ge=0, default=0)
    total_pages: int = Field(ge=0, default=0)


class PaginationParams(BaseModel):
    page: int = Field(ge=1, default=1, description="Page number")
    per_page: int = Field(ge=1, le=100, default=20, description="Items per page")


class ApiResponse(BaseModel, Generic[DataT]):
    success: bool = True
    data: DataT | None = None
    meta: PaginationMeta | None = None
    request_id: str | None = None
    message: str | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    request_id: str | None = None
