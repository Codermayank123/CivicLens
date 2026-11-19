"""
CivicLens — Analytics Schemas
Key performance indicators, distributions, and trend data models.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StatusCount(BaseModel):
    status: str
    count: int
    percentage: float = 0.0


class CategoryCount(BaseModel):
    category_id: str
    category_name: str
    count: int
    resolved_count: int = 0
    sla_compliance_rate: float | None = None


class DepartmentMetric(BaseModel):
    department_id: str
    department_name: str
    total_assigned: int
    resolved: int
    in_progress: int
    avg_resolution_hours: float | None = None
    satisfaction_rate: float | None = None
    overdue: int = 0
    on_time_resolution_rate: float = 0.0


class TrendPoint(BaseModel):
    date: str  # YYYY-MM-DD
    reported: int
    resolved: int


class HeatmapPoint(BaseModel):
    latitude: float
    longitude: float
    intensity: float = 1.0
    category: str
    title: str
    status: str
    complaint_count: int = 1


class OverviewStats(BaseModel):
    total_complaints: int
    pending_complaints: int
    in_progress_complaints: int
    resolved_complaints: int
    avg_resolution_time_hours: float
    citizen_satisfaction_percentage: float
    active_field_staff: int
    duplicate_prevented_count: int
    status_distribution: list[StatusCount] = Field(default_factory=list)
    category_distribution: list[CategoryCount] = Field(default_factory=list)
    department_metrics: list[DepartmentMetric] = Field(default_factory=list)
    trends_last_30_days: list[TrendPoint] = Field(default_factory=list)
    overdue_complaints: int = 0
    on_time_resolution_percentage: float = 0.0
    pending_human_reviews: int = 0


class StateMetric(BaseModel):
    state: str
    total_complaints: int = 0
    resolved_complaints: int = 0
    pending_complaints: int = 0
    in_progress_complaints: int = 0
    overdue_complaints: int = 0
    resolution_percentage: float = 0.0
    districts: list[dict[str, int | str | float]] = Field(default_factory=list)


class ImpactTrackerResponse(BaseModel):
    total_complaints: int
    resolved_complaints: int
    pending_complaints: int
    in_progress_complaints: int
    overdue_complaints: int
    average_resolution_hours: float
    resolution_percentage: float
    on_time_resolution_percentage: float
    citizen_satisfaction_percentage: float
    pending_human_reviews: int
    monthly_trends: list[TrendPoint] = Field(default_factory=list)
    department_metrics: list[DepartmentMetric] = Field(default_factory=list)
    state_metrics: list[StateMetric] = Field(default_factory=list)
