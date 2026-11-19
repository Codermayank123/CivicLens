"""MongoDB aggregations for accountability dashboards and map heatmaps."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from app.models.complaint import ComplaintStatus
from app.schemas.analytics import CategoryCount, DepartmentMetric, HeatmapPoint, ImpactTrackerResponse, OverviewStats, StateMetric, StatusCount, TrendPoint


class AnalyticsService:
    def __init__(self, db: Any):
        self.db = db

    async def get_overview_stats(self) -> OverviewStats:
        docs = await self.db.complaints.find({"deleted_at": None}).to_list(length=10000)
        status_counts = Counter(doc.get("status") for doc in docs)
        total = len(docs)
        resolved = status_counts[ComplaintStatus.RESOLVED.value] + status_counts[ComplaintStatus.CLOSED.value]
        pending = status_counts[ComplaintStatus.SUBMITTED.value] + status_counts[ComplaintStatus.UNDER_REVIEW.value]
        in_progress = status_counts[ComplaintStatus.ASSIGNED.value] + status_counts[ComplaintStatus.IN_PROGRESS.value]
        status_distribution = [StatusCount(status=status.value, count=status_counts[status.value], percentage=round(status_counts[status.value] / max(total, 1) * 100, 1)) for status in ComplaintStatus]
        categories = await self.db.complaint_categories.find({}).to_list(length=500)
        category_distribution = []
        for category in categories:
            category_docs = [doc for doc in docs if doc.get("category_id") == category["_id"]]
            category_distribution.append(CategoryCount(category_id=category["_id"], category_name=category["name"], count=len(category_docs), resolved_count=sum(doc.get("status") in {ComplaintStatus.RESOLVED.value, ComplaintStatus.CLOSED.value} for doc in category_docs)))
        departments = await self.db.departments.find({}).to_list(length=500)
        department_metrics = []
        durations = []
        for department in departments:
            items = [doc for doc in docs if doc.get("assigned_department_id") == department["_id"]]
            resolved_items = [doc for doc in items if doc.get("status") in {ComplaintStatus.RESOLVED.value, ComplaintStatus.CLOSED.value}]
            item_durations = [(doc["resolved_at"] - doc["created_at"]).total_seconds() / 3600 for doc in resolved_items if doc.get("resolved_at") and doc.get("created_at")]
            durations.extend(item_durations)
            department_metrics.append(DepartmentMetric(department_id=department["_id"], department_name=department["name"], total_assigned=len(items), resolved=len(resolved_items), in_progress=sum(doc.get("status") in {ComplaintStatus.ASSIGNED.value, ComplaintStatus.IN_PROGRESS.value} for doc in items), avg_resolution_hours=round(sum(item_durations) / len(item_durations), 1) if item_durations else None))
        rating_docs = await self.db.complaint_verifications.find({"rating": {"$ne": None}}).to_list(length=10000)
        avg_rating = sum(item.get("rating", 0) for item in rating_docs) / len(rating_docs) if rating_docs else 0
        active_staff = await self.db.users.count_documents({"roles": "field_staff", "is_active": True, "deleted_at": None})
        duplicate_count = await self.db.complaint_duplicates.count_documents({"confirmed": True})
        start = datetime.now(timezone.utc).date() - timedelta(days=29)
        trend = []
        for offset in range(30):
            day = start + timedelta(days=offset)
            trend.append(TrendPoint(date=day.isoformat(), reported=sum(doc.get("created_at", day).date() == day for doc in docs if doc.get("created_at")), resolved=sum(doc.get("resolved_at", day).date() == day for doc in docs if doc.get("resolved_at"))))
        overdue = sum(bool(doc.get("is_overdue")) for doc in docs)
        on_time = [doc for doc in docs if doc.get("resolved_at") and doc.get("resolution_deadline")]
        on_time_rate = sum(doc["resolved_at"] <= doc["resolution_deadline"] for doc in on_time) / len(on_time) * 100 if on_time else 0.0
        human_reviews = sum(bool(doc.get("requires_human_review")) for doc in docs)
        return OverviewStats(total_complaints=total, pending_complaints=pending, in_progress_complaints=in_progress, resolved_complaints=resolved, avg_resolution_time_hours=round(sum(durations) / len(durations), 1) if durations else 0.0, citizen_satisfaction_percentage=round(avg_rating * 20, 1), active_field_staff=active_staff, duplicate_prevented_count=duplicate_count, status_distribution=status_distribution, category_distribution=category_distribution, department_metrics=department_metrics, trends_last_30_days=trend, overdue_complaints=overdue, on_time_resolution_percentage=round(on_time_rate, 1), pending_human_reviews=human_reviews)

    async def get_impact_tracker(
        self,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        department_id: str | None = None,
        category_id: str | None = None,
        status: str | None = None,
    ) -> ImpactTrackerResponse:
        query: dict[str, Any] = {"deleted_at": None}
        if department_id:
            query["assigned_department_id"] = department_id
        if category_id:
            query["category_id"] = category_id
        if status:
            query["status"] = status
        if start_date or end_date:
            query["created_at"] = {}
            if start_date:
                query["created_at"]["$gte"] = start_date
            if end_date:
                query["created_at"]["$lte"] = end_date
        docs = await self.db.complaints.find(query).to_list(length=50000)
        total = len(docs)
        resolved = [doc for doc in docs if doc.get("status") in {ComplaintStatus.RESOLVED.value, ComplaintStatus.CITIZEN_VERIFICATION_PENDING.value, ComplaintStatus.CLOSED.value}]
        pending = [doc for doc in docs if doc.get("status") in {ComplaintStatus.SUBMITTED.value, ComplaintStatus.UNDER_REVIEW.value, ComplaintStatus.VERIFIED.value}]
        in_progress = [doc for doc in docs if doc.get("status") in {ComplaintStatus.ASSIGNED.value, ComplaintStatus.IN_PROGRESS.value, ComplaintStatus.REOPENED.value}]
        overdue = [doc for doc in docs if doc.get("is_overdue")]
        durations = [(doc["resolved_at"] - doc["created_at"]).total_seconds() / 3600 for doc in resolved if doc.get("resolved_at") and doc.get("created_at")]
        on_time = [doc for doc in resolved if doc.get("resolved_at") and doc.get("resolution_deadline")]
        ratings = await self.db.complaint_verifications.find({"rating": {"$ne": None}}).to_list(length=50000)
        satisfaction = (sum(item.get("rating", 0) for item in ratings) / len(ratings) * 20) if ratings else 0.0
        departments = await self._department_metrics(docs)
        states = await self.get_state_metrics(docs=docs)
        return ImpactTrackerResponse(
            total_complaints=total,
            resolved_complaints=len(resolved),
            pending_complaints=len(pending),
            in_progress_complaints=len(in_progress),
            overdue_complaints=len(overdue),
            average_resolution_hours=round(sum(durations) / len(durations), 1) if durations else 0.0,
            resolution_percentage=round(len(resolved) / total * 100, 1) if total else 0.0,
            on_time_resolution_percentage=round(sum(doc["resolved_at"] <= doc["resolution_deadline"] for doc in on_time) / len(on_time) * 100, 1) if on_time else 0.0,
            citizen_satisfaction_percentage=round(satisfaction, 1),
            pending_human_reviews=sum(bool(doc.get("requires_human_review")) for doc in docs),
            monthly_trends=self._trend_points(docs, days=30),
            department_metrics=departments,
            state_metrics=states,
        )

    async def get_state_metrics(self, *, docs: list[dict[str, Any]] | None = None, state: str | None = None) -> list[StateMetric]:
        docs = docs if docs is not None else await self.db.complaints.find({"deleted_at": None}).to_list(length=50000)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for doc in docs:
            name = str(doc.get("state") or (doc.get("location") or {}).get("state") or "Unspecified")
            if state and name.lower() != state.lower():
                continue
            grouped.setdefault(name, []).append(doc)
        results: list[StateMetric] = []
        for name, items in sorted(grouped.items()):
            resolved_count = sum(item.get("status") in {ComplaintStatus.RESOLVED.value, ComplaintStatus.CITIZEN_VERIFICATION_PENDING.value, ComplaintStatus.CLOSED.value} for item in items)
            districts: dict[str, list[dict[str, Any]]] = {}
            for item in items:
                districts.setdefault(str(item.get("district") or (item.get("location") or {}).get("district") or "Unspecified"), []).append(item)
            district_rows = []
            for district_name, district_items in sorted(districts.items()):
                district_resolved = sum(item.get("status") in {ComplaintStatus.RESOLVED.value, ComplaintStatus.CITIZEN_VERIFICATION_PENDING.value, ComplaintStatus.CLOSED.value} for item in district_items)
                district_rows.append({"district": district_name, "total_complaints": len(district_items), "resolved_complaints": district_resolved, "pending_complaints": len(district_items) - district_resolved, "resolution_percentage": round(district_resolved / len(district_items) * 100, 1) if district_items else 0.0})
            results.append(StateMetric(state=name, total_complaints=len(items), resolved_complaints=resolved_count, pending_complaints=sum(item.get("status") not in {ComplaintStatus.RESOLVED.value, ComplaintStatus.CITIZEN_VERIFICATION_PENDING.value, ComplaintStatus.CLOSED.value, ComplaintStatus.REJECTED.value} for item in items), in_progress_complaints=sum(item.get("status") in {ComplaintStatus.ASSIGNED.value, ComplaintStatus.IN_PROGRESS.value, ComplaintStatus.REOPENED.value} for item in items), overdue_complaints=sum(bool(item.get("is_overdue")) for item in items), resolution_percentage=round(resolved_count / len(items) * 100, 1) if items else 0.0, districts=district_rows))
        return results

    async def _department_metrics(self, docs: list[dict[str, Any]]) -> list[DepartmentMetric]:
        departments = await self.db.departments.find({"is_active": True}).to_list(length=500)
        results = []
        for department in departments:
            items = [doc for doc in docs if doc.get("assigned_department_id") == department["_id"]]
            resolved_items = [doc for doc in items if doc.get("status") in {ComplaintStatus.RESOLVED.value, ComplaintStatus.CITIZEN_VERIFICATION_PENDING.value, ComplaintStatus.CLOSED.value}]
            durations = [(doc["resolved_at"] - doc["created_at"]).total_seconds() / 3600 for doc in resolved_items if doc.get("resolved_at") and doc.get("created_at")]
            slas = [doc for doc in resolved_items if doc.get("resolution_deadline") and doc.get("resolved_at")]
            results.append(DepartmentMetric(department_id=department["_id"], department_name=department["name"], total_assigned=len(items), resolved=len(resolved_items), in_progress=sum(doc.get("status") in {ComplaintStatus.ASSIGNED.value, ComplaintStatus.IN_PROGRESS.value, ComplaintStatus.REOPENED.value} for doc in items), avg_resolution_hours=round(sum(durations) / len(durations), 1) if durations else None, overdue=sum(bool(doc.get("is_overdue")) for doc in items), on_time_resolution_rate=round(sum(doc["resolved_at"] <= doc["resolution_deadline"] for doc in slas) / len(slas) * 100, 1) if slas else 0.0))
        return results

    @staticmethod
    def _trend_points(docs: list[dict[str, Any]], days: int = 30) -> list[TrendPoint]:
        start = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
        points = []
        for offset in range(days):
            day = start + timedelta(days=offset)
            points.append(TrendPoint(date=day.isoformat(), reported=sum(doc.get("created_at").date() == day for doc in docs if doc.get("created_at")), resolved=sum(doc.get("resolved_at").date() == day for doc in docs if doc.get("resolved_at"))))
        return points

    async def get_heatmap_points(self) -> list[HeatmapPoint]:
        docs = await self.db.complaints.find({"deleted_at": None, "latitude": {"$ne": None}, "longitude": {"$ne": None}}).sort("created_at", -1).limit(500).to_list(length=500)
        category_ids = {doc.get("category_id") for doc in docs}
        categories = await self.db.complaint_categories.find({"_id": {"$in": list(category_ids)}}).to_list(length=500) if category_ids else []
        names = {item["_id"]: item["name"] for item in categories}
        points = []
        for doc in docs:
            intensity = {"critical": 2.0, "high": 1.5, "low": 0.6}.get(doc.get("priority"), 1.0)
            points.append(HeatmapPoint(latitude=doc["latitude"], longitude=doc["longitude"], intensity=intensity, category=names.get(doc.get("category_id"), "General"), title=doc["title"], status=doc.get("status", "submitted")))
        return points

    async def get_public_heatmap(self) -> list[HeatmapPoint]:
        """Return privacy-safe hotspot clusters, not individual citizen reports."""
        docs = await self.db.complaints.find({"deleted_at": None, "latitude": {"$ne": None}, "longitude": {"$ne": None}}).to_list(length=10000)
        categories = await self.db.complaint_categories.find({}).to_list(length=500)
        names = {item["_id"]: item["name"] for item in categories}
        clusters: dict[tuple[float, float, str], dict[str, Any]] = {}
        for doc in docs:
            key = (round(float(doc["latitude"]), 3), round(float(doc["longitude"]), 3), names.get(doc.get("category_id"), "General"))
            bucket = clusters.setdefault(key, {"count": 0, "open": 0})
            bucket["count"] += 1
            if doc.get("status") not in {ComplaintStatus.CLOSED.value, ComplaintStatus.REJECTED.value}:
                bucket["open"] += 1
        return [HeatmapPoint(latitude=lat, longitude=lon, intensity=min(3.0, 0.75 + item["count"] * 0.25), category=category, title=f"{item['count']} related reports", status="open" if item["open"] else "resolved", complaint_count=item["count"]) for (lat, lon, category), item in clusters.items()]

    async def get_accountability(self) -> list[dict[str, Any]]:
        docs = await self.db.complaints.find({"deleted_at": None}).to_list(length=10000)
        departments = await self.db.departments.find({"is_active": True}).sort("name", 1).to_list(length=500)
        result = []
        for department in departments:
            items = [doc for doc in docs if doc.get("assigned_department_id") == department["_id"]]
            resolved = sum(doc.get("status") in {ComplaintStatus.RESOLVED.value, ComplaintStatus.CLOSED.value} for doc in items)
            pending = sum(doc.get("status") not in {ComplaintStatus.RESOLVED.value, ComplaintStatus.CLOSED.value, ComplaintStatus.REJECTED.value} for doc in items)
            result.append({"department_id": department["_id"], "department_name": department["name"], "code": department["code"], "total_complaints": len(items), "resolved_complaints": resolved, "pending_complaints": pending, "resolution_rate": round((resolved / len(items)) * 100, 1) if items else 0.0})
        return result
