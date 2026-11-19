"""MongoDB complaint lifecycle service.

All state transitions are explicit, role checked, and written to the immutable
status-history and audit collections. AI suggestions remain advisory metadata.
"""

from __future__ import annotations

from datetime import timedelta
import hashlib
import mimetypes
import random
import string
from math import asin, cos, radians, sin, sqrt
from typing import Any

from app.core.mongo import model_to_doc, utc_now
from app.config import get_settings
from app.exceptions import AccountNotVerifiedError, ForbiddenError, NotFoundError, ValidationError
from app.models.complaint import (
    Complaint,
    ComplaintAssignment,
    ComplaintComment,
    ComplaintMedia,
    ComplaintStatus,
    ComplaintStatusHistory,
    ComplaintVerification,
    MediaType,
    VerificationAction,
)
from app.models.ai_prediction import AIPrediction
from app.models.user import User
from app.schemas.auth import UserBrief
from app.schemas.complaint import (
    AssignmentUpdate,
    CommentCreate,
    CommentItem,
    ComplaintCreate,
    ComplaintFilters,
    ComplaintListItem,
    ComplaintResponse,
    DuplicateCandidate,
    MediaItem,
    ModerationReviewRequest,
    StatusHistoryItem,
    StatusUpdate,
    VerificationItem,
    VerificationRequest,
    ReopenRequest,
)
from app.schemas.department import CategoryResponse, DepartmentResponse
from app.services.ai_client import ai_client
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.rewards_service import RewardsService
from app.services.storage_service import is_managed_media_url, signed_media_url, storage_service
from app.services.deadline_service import calculate_deadline


def generate_public_id(category_slug: str | None = None) -> str:
    prefix = (category_slug[:3] if category_slug else "CIV").upper()
    return f"{prefix}-{''.join(random.choices(string.digits, k=6))}"


def _evaluate_ai_outcome(verification: dict[str, Any], text_result: dict[str, Any]) -> tuple[str, str]:
    """Convert advisory signals into a safe three-level workflow decision."""
    if verification.get("provider_unavailable") or text_result.get("provider_unavailable"):
        return "human_review", "AI analysis is unavailable; an authorized officer must review this complaint."
    spam = verification.get("spam_check") or {}
    confidence = float(verification.get("confidence", text_result.get("confidence", 0.0)) or 0.0)
    relevant = bool(text_result.get("is_relevant", False))
    suspicious = bool(verification.get("suspicious", False))
    duplicate_risk = float(verification.get("duplicate_risk", 0.0) or 0.0)
    evidence = verification.get("evidence") or []
    evidence_review = any(item.get("requires_human_review", False) or item.get("suspicious", False) for item in evidence if isinstance(item, dict))

    # Permanent rejection is reserved for high-signal spam/irrelevance. Low
    # confidence, provider outages, duplicates, and uncertain evidence always
    # go to a human queue instead.
    if (bool(spam.get("is_spam")) and float(spam.get("spam_score", 0.0) or 0.0) >= 0.9 and not relevant) or (not relevant and confidence <= 0.12 and not evidence):
        reason = "; ".join(spam.get("reasons") or []) or str(text_result.get("message") or "The submission does not describe a valid civic issue.")
        return "rejected", reason
    if verification.get("requires_human_review") or suspicious or duplicate_risk >= 0.4 or evidence_review or not relevant or confidence < 0.75:
        reasons = verification.get("suspicious_reasons") or []
        if duplicate_risk >= 0.4:
            reasons = [*reasons, "Potentially duplicate complaint"]
        if evidence_review:
            reasons = [*reasons, "Evidence needs human review"]
        return "human_review", "; ".join(str(item) for item in reasons) or "AI confidence is insufficient for automatic acceptance."
    return "accepted", "Complaint and evidence signals are consistent with the selected civic category."


class ComplaintService:
    def __init__(self, db: Any):
        self.db = db
        self.notifications = NotificationService(db)

    async def create(self, user: User, data: ComplaintCreate) -> ComplaintResponse:
        if "citizen" in user.roles and not user.identity_verified:
            raise AccountNotVerifiedError()
        if any(not is_managed_media_url(url) for url in data.media_urls):
            raise ValidationError("Evidence must be uploaded through CivicLens before submission")
        category = await self.db.complaint_categories.find_one({"_id": data.category_id, "is_active": True})
        if not category:
            raise ValidationError("Invalid or inactive complaint category")
        ai_verification = await ai_client.verify_complaint(
            title=data.title,
            description=data.description,
            selected_category=category["slug"],
            media_urls=data.media_urls,
        )
        text_result = ai_verification.get("text", ai_verification)
        # Count this citizen's complaints submitted in the last 24 hours.
        submission_window = utc_now() - timedelta(hours=24)
        user_submission_count = await self.db.complaints.count_documents({
            "created_by": user.id,
            "created_at": {"$gte": submission_window},
            "deleted_at": None,
        })
        # Run advisory spam detection.
        spam_result = await ai_client.check_spam(
            text=f"{data.title}. {data.description}",
            user_submission_count=user_submission_count,
        )
        ai_verification["spam_check"] = spam_result
        # Suspicious or unavailable assessments require human review.
        if spam_result["is_spam"] or spam_result["check_unavailable"]:
            ai_verification["requires_human_review"] = True
        duplicate_candidates = await self.check_potential_duplicates(
            title=data.title,
            description=data.description,
            category_id=data.category_id,
            latitude=data.latitude,
            longitude=data.longitude,
        )
        if duplicate_candidates:
            ai_verification["duplicate_candidates"] = [item.model_dump(mode="json") for item in duplicate_candidates[:5]]
            ai_verification["duplicate_risk"] = duplicate_candidates[0].similarity_score
            ai_verification["requires_human_review"] = True
        ai_outcome, ai_reason = _evaluate_ai_outcome(ai_verification, text_result)
        now = utc_now()
        deadline = calculate_deadline(now, data.priority.value, category)
        complaint = Complaint(
            public_id=generate_public_id(category["slug"]), title=data.title.strip(), description=data.description.strip(),
            category_id=data.category_id,
            priority=data.priority,
            status=ComplaintStatus.REJECTED if ai_outcome == "rejected" else ComplaintStatus.SUBMITTED,
            latitude=data.latitude, longitude=data.longitude,
            location=Complaint.make_geojson(data.latitude, data.longitude), address=data.address, landmark=data.landmark,
            state=data.state, district=data.district, city=data.city, locality=data.locality,
            sub_district=data.sub_district, block=data.block, gram_panchayat=data.gram_panchayat,
            ward=data.ward, pincode=data.pincode,
            original_language=data.language,
            created_by=user.id, assigned_department_id=category.get("department_id"), ai_category=text_result.get("category"),
            ai_confidence=text_result.get("confidence"), ai_is_mock=bool(ai_verification.get("is_mock", text_result.get("is_mock", False))),
            ai_verification=ai_verification,
            requires_human_review=ai_outcome == "human_review",
            ai_outcome=ai_outcome,
            ai_reason=ai_reason,
            ai_model_version=str(ai_verification.get("model_version") or text_result.get("model_version") or "civiclens-ai-1"),
            ai_verified_at=now,
            duplicate_group_id=duplicate_candidates[0].id if duplicate_candidates else None,
            duplicate_score=duplicate_candidates[0].similarity_score if duplicate_candidates else None,
            voice_description_url=data.voice_description_url, created_at=now, updated_at=now,
            resolution_deadline=deadline,
        )
        ai_verification["outcome"] = ai_outcome
        ai_verification["reason"] = ai_reason
        ai_verification["model_version"] = complaint.ai_model_version
        for _ in range(3):
            if not await self.db.complaints.find_one({"public_id": complaint.public_id}):
                break
            complaint.public_id = generate_public_id(category["slug"])
        await self.db.complaints.insert_one(model_to_doc(complaint))
        await self.db.ai_predictions.insert_one(model_to_doc(AIPrediction(
            complaint_id=complaint.id,
            prediction_type="complaint_verification",
            predicted_category=complaint.ai_category,
            confidence=complaint.ai_confidence,
            is_mock=complaint.ai_is_mock,
            raw_output=ai_verification,
        )))
        for candidate in duplicate_candidates[:5]:
            await self.db.complaint_duplicates.insert_one({
                "_id": f"duplicate:{complaint.id}:{candidate.id}",
                "complaint_id": complaint.id,
                "duplicate_of_id": candidate.id,
                "similarity_score": candidate.similarity_score,
                "confirmed": None,
                "created_at": now,
            })
        for index, url in enumerate(data.media_urls):
            metadata = data.media_metadata[index] if index < len(data.media_metadata) else None
            file_name = metadata.file_name if metadata else url.rsplit("/", 1)[-1]
            mime_type = metadata.mime_type if metadata else mimetypes.guess_type(file_name)[0] or "application/octet-stream"
            media = ComplaintMedia(
                complaint_id=complaint.id,
                media_type=MediaType.VIDEO if mime_type.startswith("video/") else MediaType.IMAGE,
                file_url=url, file_name=file_name, file_size=metadata.file_size if metadata else 0,
                mime_type=mime_type, uploaded_by=user.id,
            )
            await self.db.complaint_media.insert_one(model_to_doc(media))
        history = ComplaintStatusHistory(complaint_id=complaint.id, to_status=complaint.status, changed_by=user.id, reason="Issue reported by citizen.")
        await self.db.complaint_status_history.insert_one(model_to_doc(history))
        notification_title = "Complaint rejected" if ai_outcome == "rejected" else ("Complaint under human review" if ai_outcome == "human_review" else "Complaint verified")
        notification_kind = "complaint_rejected" if ai_outcome == "rejected" else ("verification_required" if ai_outcome == "human_review" else "complaint_submitted")
        notification_message = {
            "accepted": "Your complaint has been successfully verified and forwarded to the concerned department.",
            "human_review": "Your complaint has been submitted successfully and is currently under verification by our review team.",
            "rejected": "Your complaint could not be verified. Please review the reason and submit accurate information.",
        }[ai_outcome]
        await self.notifications.create_notification(
            user.id,
            notification_title,
            f"#{complaint.public_id}: {notification_message} Reason: {ai_reason}",
            notification_kind,
            complaint.id,
            {"ai_outcome": ai_outcome, "ai_reason": ai_reason, "resolution_deadline": deadline.isoformat()},
        )
        officers = await self.db.users.find({
            "roles": "officer",
            "department_id": category.get("department_id"),
            "is_active": True,
            "is_suspended": {"$ne": True},
            "deleted_at": None,
        }).to_list(length=100)
        for officer in officers if ai_outcome != "rejected" else []:
            await self.notifications.create_notification(
                officer["_id"],
                "New complaint in your department",
                f"Complaint #{complaint.public_id} is awaiting {'human verification' if complaint.requires_human_review else 'triage'}.",
                "complaint_submitted",
                complaint.id,
                {"requires_human_review": complaint.requires_human_review, "ai_outcome": ai_outcome},
            )
        await AuditService(self.db).record(action="complaint.create", resource_type="complaint", resource_id=complaint.id, actor_id=user.id, details={"public_id": complaint.public_id, "ai_is_mock": complaint.ai_is_mock})
        response = await self.get_by_id(complaint.id)
        return self._filter_internal_ai(response, user)

    async def get_by_id(self, complaint_id: str) -> ComplaintResponse:
        doc = await self.db.complaints.find_one({"_id": complaint_id, "deleted_at": None})
        if not doc:
            raise NotFoundError("Complaint not found")
        return await self._to_response(doc)

    async def get_by_public_id(self, public_id: str) -> ComplaintResponse:
        doc = await self.db.complaints.find_one({"public_id": public_id, "deleted_at": None})
        if not doc:
            raise NotFoundError(f"Complaint with ID {public_id} not found")
        return await self._to_response(doc)

    async def get_by_id_for_user(self, complaint_id: str, user: User) -> ComplaintResponse:
        response = await self.get_by_id(complaint_id)
        return self._authorize_complaint_read(response, user)

    async def get_by_public_id_for_user(self, public_id: str, user: User) -> ComplaintResponse:
        response = await self.get_by_public_id(public_id)
        return self._authorize_complaint_read(response, user)

    def _authorize_complaint_read(self, response: ComplaintResponse, user: User) -> ComplaintResponse:
        roles = set(user.roles)
        allowed = "admin" in roles or response.created_by == user.id or (roles.intersection({"officer", "department_head"}) and response.assigned_department_id == user.department_id) or ("field_staff" in roles and response.assigned_staff_id == user.id)
        if not allowed:
            raise ForbiddenError("You do not have access to this complaint")
        if not roles.intersection({"admin", "officer", "department_head", "field_staff"}):
            response.comments = [comment for comment in response.comments if not comment.is_internal]
        return self._filter_internal_ai(response, user)

    @staticmethod
    def _filter_internal_ai(response: ComplaintResponse, user: User) -> ComplaintResponse:
        """Keep moderation evidence restricted to administrators and officers."""
        if not set(user.roles).intersection({"admin", "officer"}):
            response.ai_verification = {}
        return response

    async def list_complaints(self, filters: ComplaintFilters, user: User) -> tuple[list[ComplaintListItem], int]:
        roles = set(user.roles)
        query: dict[str, Any] = {"deleted_at": None}
        if "admin" not in roles:
            if roles.intersection({"officer", "department_head"}):
                query["$or"] = [
                    {"assigned_department_id": user.department_id} if user.department_id else {"assigned_department_id": "__none__"},
                    {"assigned_department_id": None},
                ]
            elif "field_staff" in roles:
                query["assigned_staff_id"] = user.id
            else:
                query["created_by"] = user.id
        if filters.status:
            query["status"] = filters.status.value
        if filters.priority:
            query["priority"] = filters.priority.value
        if filters.category_id:
            query["category_id"] = filters.category_id
        if filters.state:
            query["state"] = filters.state
        if filters.district:
            query["district"] = filters.district
        if "admin" in roles:
            if filters.department_id:
                query["assigned_department_id"] = filters.department_id
            if filters.assigned_staff_id:
                query["assigned_staff_id"] = filters.assigned_staff_id
            if filters.created_by:
                query["created_by"] = filters.created_by
        elif roles.intersection({"officer", "department_head"}):
            if filters.department_id and filters.department_id != user.department_id:
                raise ForbiddenError("Department users may only view their own department")
            if filters.assigned_staff_id:
                staff = await self.db.users.find_one({"_id": filters.assigned_staff_id, "department_id": user.department_id})
                if not staff:
                    raise ForbiddenError("Department users may only view staff in their own department")
                query["assigned_staff_id"] = filters.assigned_staff_id
        elif "field_staff" in roles:
            if filters.assigned_staff_id and filters.assigned_staff_id != user.id:
                raise ForbiddenError("Field staff may only view their assigned complaints")
        elif filters.created_by and filters.created_by != user.id:
            raise ForbiddenError("Citizens may only view their own complaints")
        if filters.start_date or filters.end_date:
            query["created_at"] = {}
            if filters.start_date:
                query["created_at"]["$gte"] = filters.start_date
            if filters.end_date:
                query["created_at"]["$lte"] = filters.end_date
        if filters.search:
            escaped = filters.search.strip()
            query["$or"] = [{"title": {"$regex": escaped, "$options": "i"}}, {"description": {"$regex": escaped, "$options": "i"}}, {"public_id": {"$regex": escaped, "$options": "i"}}, {"address": {"$regex": escaped, "$options": "i"}}]
        total = await self.db.complaints.count_documents(query)
        docs = await self.db.complaints.find(query).sort("created_at", -1).skip((filters.page - 1) * filters.per_page).limit(filters.per_page).to_list(length=filters.per_page)
        items = []
        for doc in docs:
            category = await self.db.complaint_categories.find_one({"_id": doc.get("category_id")})
            department = await self.db.departments.find_one({"_id": doc.get("assigned_department_id")}) if doc.get("assigned_department_id") else None
            staff = await self.db.users.find_one({"_id": doc.get("assigned_staff_id")}) if doc.get("assigned_staff_id") else None
            media_count = await self.db.complaint_media.count_documents({"complaint_id": doc["_id"]})
            first_media = await self.db.complaint_media.find_one({"complaint_id": doc["_id"]}, sort=[("created_at", 1)])
            items.append(ComplaintListItem(
                id=doc["_id"], public_id=doc["public_id"], title=doc["title"], category_name=category.get("name") if category else None,
                category_slug=category.get("slug") if category else None, category_icon=category.get("icon") if category else None,
                priority=doc["priority"], status=doc["status"], address=doc.get("address"), state=doc.get("state"), district=doc.get("district"), latitude=doc.get("latitude"), longitude=doc.get("longitude"),
                created_at=doc["created_at"], updated_at=doc["updated_at"], creator_name=(await self._user_name(doc.get("created_by"))),
                assigned_department_name=department.get("name") if department else None, assigned_staff_name=staff.get("full_name") if staff else None,
                media_count=media_count, thumbnail_url=signed_media_url(first_media["file_url"]) if first_media else None,
                requires_human_review=doc.get("requires_human_review", not doc.get("ai_category") or not doc.get("ai_confidence") or doc.get("ai_confidence", 0) < 0.5),
                ai_is_mock=doc.get("ai_is_mock", False),
                ai_outcome=doc.get("ai_outcome", "human_review"),
                resolution_deadline=doc.get("resolution_deadline"),
                is_overdue=bool(doc.get("is_overdue", False)),
                escalation_level=int(doc.get("escalation_level", 0)),
            ))
        return items, total

    async def list_ai_review_queue(self, user: User, page: int = 1, per_page: int = 50) -> tuple[list[ComplaintResponse], int]:
        """Return complaints whose AI decision requires an authorized human."""
        roles = set(user.roles)
        query: dict[str, Any] = {"deleted_at": None, "requires_human_review": True}
        if "admin" not in roles:
            if roles.intersection({"officer", "department_head"}):
                query["assigned_department_id"] = user.department_id or "__none__"
            else:
                raise ForbiddenError("Only authorized department reviewers can access the AI review queue")
        total = await self.db.complaints.count_documents(query)
        docs = await self.db.complaints.find(query).sort("created_at", 1).skip((page - 1) * per_page).limit(per_page).to_list(length=per_page)
        return [await self._to_response(doc) for doc in docs], total

    async def update_status(self, complaint_id: str, user: User, data: StatusUpdate) -> ComplaintResponse:
        doc = await self._get_doc(complaint_id)
        old = ComplaintStatus(doc["status"])
        roles = set(user.roles)
        if "admin" not in roles:
            if roles.intersection({"officer", "department_head"}) and doc.get("assigned_department_id") != user.department_id:
                raise ForbiddenError("Officers may only update complaints in their department")
            if "field_staff" in roles and (doc.get("assigned_staff_id") != user.id or data.status not in {ComplaintStatus.IN_PROGRESS, ComplaintStatus.RESOLVED}):
                raise ForbiddenError("Field staff may only update assigned work")
            if data.status == ComplaintStatus.REJECTED and not (data.notes or "").strip():
                raise ValidationError("A rejection reason is required")
            allowed = {
                ComplaintStatus.SUBMITTED: {ComplaintStatus.UNDER_REVIEW, ComplaintStatus.ASSIGNED, ComplaintStatus.REJECTED},
                ComplaintStatus.UNDER_REVIEW: {ComplaintStatus.VERIFIED, ComplaintStatus.ASSIGNED, ComplaintStatus.REJECTED},
                ComplaintStatus.VERIFIED: {ComplaintStatus.ASSIGNED, ComplaintStatus.REJECTED},
                ComplaintStatus.ASSIGNED: {ComplaintStatus.IN_PROGRESS, ComplaintStatus.REJECTED},
                ComplaintStatus.IN_PROGRESS: {ComplaintStatus.RESOLVED, ComplaintStatus.REJECTED},
                ComplaintStatus.REOPENED: {ComplaintStatus.ASSIGNED, ComplaintStatus.IN_PROGRESS},
                ComplaintStatus.RESOLVED: {ComplaintStatus.CITIZEN_VERIFICATION_PENDING, ComplaintStatus.REOPENED},
            }
            if data.status not in allowed.get(old, set()):
                raise ValidationError(f"Complaint cannot move from {old.value} to {data.status.value}")
        evidence = list(data.resolution_evidence)
        if not evidence and data.resolution_media_urls:
            legacy_stages = ["before", "after"] if len(data.resolution_media_urls) >= 2 else ["supporting"] * len(data.resolution_media_urls)
            evidence = [{"media_url": url, "stage": legacy_stages[index]} for index, url in enumerate(data.resolution_media_urls)]
        next_status = data.status
        is_resolution = data.status in {ComplaintStatus.RESOLVED, ComplaintStatus.CITIZEN_VERIFICATION_PENDING}
        if is_resolution and not (data.notes or "").strip():
            raise ValidationError("Resolution remarks are required before resolving a complaint")
        if "field_staff" in roles and data.status == ComplaintStatus.RESOLVED:
            stages = {item.stage if hasattr(item, "stage") else item.get("stage") for item in evidence}
            if stages != {"before", "after"}:
                raise ValidationError("Upload both before and after work photographs before submitting resolution")
            next_status = ComplaintStatus.CITIZEN_VERIFICATION_PENDING
        if is_resolution and not evidence and not get_settings().ALLOW_RESOLUTION_WITHOUT_EVIDENCE:
            raise ValidationError("Final evidence photographs are required before resolving a complaint")
        if len(evidence) > 10:
            raise ValidationError("A maximum of 10 resolution photographs may be submitted")
        evidence_urls: set[str] = set()
        for item in evidence:
            url = item.media_url if hasattr(item, "media_url") else item["media_url"]
            if not is_managed_media_url(url):
                raise ValidationError("Resolution evidence must be uploaded through CivicLens")
            if url in evidence_urls:
                raise ValidationError("Resolution evidence cannot contain duplicate files")
            evidence_urls.add(url)
            content = await storage_service.read_file_url(url)
            if content is None:
                raise ValidationError("Every resolution photograph must be stored before the status is updated")
            stage = item.stage if hasattr(item, "stage") else item.get("stage")
            caption = item.caption if hasattr(item, "caption") else item.get("caption")
            mime_type = mimetypes.guess_type(url)[0] or "image/jpeg"
            if not mime_type.startswith("image/"):
                raise ValidationError("Final resolution evidence must be photographs")
            media = ComplaintMedia(complaint_id=complaint_id, media_type=MediaType.IMAGE, file_url=url, file_name=url.rsplit("/", 1)[-1], file_size=len(content), mime_type=mime_type, sha256=hashlib.sha256(content).hexdigest(), is_resolution_evidence=True, evidence_stage=stage, caption=caption, uploaded_by=user.id)
            await self.db.complaint_media.insert_one(model_to_doc(media))
        now = utc_now()
        update = {"status": next_status.value, "updated_at": now}
        if data.notes:
            update["resolution_notes"] = data.notes
        if next_status in {ComplaintStatus.RESOLVED, ComplaintStatus.CITIZEN_VERIFICATION_PENDING}:
            update["resolved_at"] = now
            update["resolution_submitted_at"] = now
            update["is_overdue"] = False
        if next_status == ComplaintStatus.CLOSED:
            update["closed_at"] = now
        await self.db.complaints.update_one({"_id": complaint_id}, {"$set": update})
        history = ComplaintStatusHistory(complaint_id=complaint_id, from_status=old, to_status=next_status, changed_by=user.id, reason=data.notes or f"Status changed from {old.value} to {next_status.value}")
        await self.db.complaint_status_history.insert_one(model_to_doc(history))
        status_name = next_status.value.replace("_", " ").title()
        notification_type = "verification_required" if next_status == ComplaintStatus.CITIZEN_VERIFICATION_PENDING else ("complaint_rejected" if next_status == ComplaintStatus.REJECTED else "status_update")
        await self.notifications.create_notification(doc["created_by"], f"Complaint status: {status_name}", f"Your complaint #{doc['public_id']} is now {status_name}. {data.notes or ''}".strip(), notification_type, complaint_id, {"remarks": data.notes, "status": next_status.value, "resolution": is_resolution})
        if next_status == ComplaintStatus.CITIZEN_VERIFICATION_PENDING and "field_staff" in roles:
            officers = await self.db.users.find({"roles": {"$in": ["officer", "department_head"]}, "department_id": doc.get("assigned_department_id"), "is_active": True, "deleted_at": None}).to_list(length=100)
            for officer in officers:
                await self.notifications.create_notification(officer["_id"], "Field work submitted for verification", f"Review the work evidence for complaint #{doc['public_id']}.", "status_update", complaint_id)
        if doc.get("assigned_staff_id") and doc.get("assigned_staff_id") != user.id:
            await self.notifications.create_notification(doc["assigned_staff_id"], f"Complaint status: {status_name}", f"Complaint #{doc['public_id']} is now {status_name}.", "status_update", complaint_id)
        await AuditService(self.db).record(action="complaint.status_change", resource_type="complaint", resource_id=complaint_id, actor_id=user.id, details={"from": old.value, "to": next_status.value, "reason": data.notes, "evidence_count": len(evidence)})
        response = await self.get_by_id(complaint_id)
        return self._filter_internal_ai(response, user)

    async def assign(self, complaint_id: str, user: User, data: AssignmentUpdate) -> ComplaintResponse:
        doc = await self._get_doc(complaint_id)
        roles = set(user.roles)
        target_department = data.department_id or doc.get("assigned_department_id")
        if "admin" not in roles and (
            not roles.intersection({"officer", "department_head"})
            or target_department != user.department_id
            or (doc.get("assigned_department_id") not in {None, user.department_id})
        ):
            raise ForbiddenError("Officers may only assign complaints within their department")
        if not target_department or not await self.db.departments.find_one({"_id": target_department, "is_active": True}):
            raise ValidationError("The selected department is invalid or inactive")
        if data.staff_id:
            staff = await self.db.users.find_one({"_id": data.staff_id, "is_active": True, "is_suspended": {"$ne": True}, "roles": "field_staff", "department_id": target_department})
            if not staff:
                raise ValidationError("The selected assignee must be active field staff in this department")
        now = utc_now()
        previous_staff_id = doc.get("assigned_staff_id")
        update = {"assigned_department_id": target_department, "updated_at": now}
        if data.staff_id:
            update.update({"assigned_staff_id": data.staff_id, "status": ComplaintStatus.ASSIGNED.value})
        else:
            update["assigned_staff_id"] = None
        await self.db.complaints.update_one({"_id": complaint_id}, {"$set": update})
        assignment = ComplaintAssignment(complaint_id=complaint_id, department_id=target_department, assigned_to=data.staff_id, assigned_by=user.id, notes=data.notes)
        await self.db.complaint_assignments.insert_one(model_to_doc(assignment))
        await self.notifications.create_notification(
            doc["created_by"],
            "Complaint assigned",
            f"Complaint #{doc['public_id']} has been assigned to {target_department}.",
            "assignment",
            complaint_id,
            {"remarks": data.notes, "status": ComplaintStatus.ASSIGNED.value},
        )
        if data.staff_id:
            await self.notifications.create_notification(data.staff_id, "New field task", f"Complaint #{doc['public_id']} has been assigned to you.", "assignment", complaint_id)
        if previous_staff_id and previous_staff_id != data.staff_id:
            await self.notifications.create_notification(previous_staff_id, "Field task reassigned", f"Complaint #{doc['public_id']} has been reassigned to another team member.", "assignment", complaint_id)
        await AuditService(self.db).record(action="complaint.assign", resource_type="complaint", resource_id=complaint_id, actor_id=user.id, details={"department_id": target_department, "staff_id": data.staff_id})
        response = await self.get_by_id(complaint_id)
        return self._filter_internal_ai(response, user)

    async def verify_resolution(self, complaint_id: str, user: User, data: VerificationRequest) -> ComplaintResponse:
        doc = await self._get_doc(complaint_id)
        if doc.get("created_by") != user.id and "admin" not in user.roles:
            raise ForbiddenError("Only the reporting citizen can verify this resolution")
        if doc.get("status") not in {ComplaintStatus.RESOLVED.value, ComplaintStatus.CITIZEN_VERIFICATION_PENDING.value}:
            raise ValidationError("This complaint is not awaiting citizen verification")
        now = utc_now()
        verification = ComplaintVerification(complaint_id=complaint_id, verified_by=user.id, action=data.action, reason=data.feedback, rating=data.rating)
        await self.db.complaint_verifications.insert_one(model_to_doc(verification))
        next_status = ComplaintStatus.CLOSED if data.action == VerificationAction.APPROVED else ComplaintStatus.REOPENED
        await self.db.complaints.update_one({"_id": complaint_id}, {"$set": {"status": next_status.value, "closed_at": now if next_status == ComplaintStatus.CLOSED else None, "updated_at": now}})
        history = ComplaintStatusHistory(complaint_id=complaint_id, from_status=ComplaintStatus(doc["status"]), to_status=next_status, changed_by=user.id, reason=data.feedback or f"Citizen {data.action.value} resolution")
        await self.db.complaint_status_history.insert_one(model_to_doc(history))
        if next_status == ComplaintStatus.CLOSED:
            rewards = RewardsService(self.db)
            await rewards.award_points(user.id, 50, "verified_report", complaint_id)
            for supporter_id in doc.get("supporters", []):
                await rewards.award_points(supporter_id, 5, "validated_support", complaint_id)
        await AuditService(self.db).record(action="complaint.verify", resource_type="complaint", resource_id=complaint_id, actor_id=user.id, details={"action": data.action.value, "rating": data.rating})
        response = await self.get_by_id(complaint_id)
        return self._filter_internal_ai(response, user)

    async def review_ai_moderation(
        self,
        complaint_id: str,
        user: User,
        data: ModerationReviewRequest,
    ) -> ComplaintResponse:
        """Record an authorized human decision about the advisory AI assessment."""
        doc = await self._get_doc(complaint_id)
        roles = set(user.roles)
        if "admin" not in roles and (not roles.intersection({"officer", "department_head"}) or doc.get("assigned_department_id") != user.department_id):
            raise ForbiddenError("Only the responsible department officer or an administrator can review AI moderation")
        previous = (doc.get("ai_verification") or {}).get("moderation")
        action_map = {
            "not_spam": "approve",
            "confirmed_spam": "reject",
            "escalated": "request_information",
        }
        normalized_action = action_map.get(data.action, data.action)
        verification = dict(doc.get("ai_verification") or {})
        reviewed_at = utc_now()
        verification["moderation"] = {
            "status": "reviewed",
            "action": normalized_action,
            "reason": data.reason.strip(),
            "reviewed_by": user.id,
            "reviewed_at": reviewed_at,
        }
        next_status = doc.get("status")
        if normalized_action == "approve" and next_status in {ComplaintStatus.SUBMITTED.value, ComplaintStatus.UNDER_REVIEW.value}:
            next_status = ComplaintStatus.VERIFIED.value
        elif normalized_action == "reject":
            next_status = ComplaintStatus.REJECTED.value
        elif normalized_action == "request_information":
            next_status = ComplaintStatus.UNDER_REVIEW.value
        await self.db.complaints.update_one(
            {"_id": complaint_id},
            {"$set": {"ai_verification": verification, "requires_human_review": normalized_action == "request_information", "ai_outcome": "accepted" if normalized_action == "approve" else ("rejected" if normalized_action == "reject" else "human_review"), "ai_reason": data.reason.strip(), "status": next_status, "updated_at": reviewed_at}},
        )
        await self.db.complaint_status_history.insert_one(model_to_doc(ComplaintStatusHistory(
            complaint_id=complaint_id,
            from_status=ComplaintStatus(doc.get("status", ComplaintStatus.SUBMITTED.value)),
            to_status=ComplaintStatus(next_status),
            changed_by=user.id,
            reason=f"Human AI review: {normalized_action}. {data.reason.strip()}",
        )))
        if normalized_action == "reject":
            await self.notifications.create_notification(doc["created_by"], "Complaint rejected", f"Your complaint #{doc['public_id']} could not be verified. {data.reason.strip()}", "complaint_rejected", complaint_id)
        elif normalized_action == "approve":
            await self.notifications.create_notification(doc["created_by"], "Complaint approved", "Your complaint has been successfully verified and forwarded to the concerned department.", "complaint_submitted", complaint_id)
        else:
            await self.notifications.create_notification(doc["created_by"], "More information requested", f"Please provide additional information for complaint #{doc['public_id']}. {data.reason.strip()}", "verification_required", complaint_id)
        await AuditService(self.db).record(
            action="complaint.ai_moderation_review",
            resource_type="complaint",
            resource_id=complaint_id,
            actor_id=user.id,
            details={"previous": previous, "action": data.action, "reason": data.reason.strip()},
        )
        return await self.get_by_id_for_user(complaint_id, user)

    async def reopen(self, complaint_id: str, user: User, data: ReopenRequest) -> ComplaintResponse:
        doc = await self._get_doc(complaint_id)
        if doc.get("created_by") != user.id and "admin" not in user.roles:
            raise ForbiddenError("Only the reporting citizen can reopen this complaint")
        if doc.get("status") not in {ComplaintStatus.CLOSED.value, ComplaintStatus.RESOLVED.value}:
            raise ValidationError("Only resolved or closed complaints can be reopened")
        now = utc_now()
        await self.db.complaints.update_one({"_id": complaint_id}, {"$set": {"status": ComplaintStatus.REOPENED.value, "updated_at": now}, "$unset": {"closed_at": ""}})
        history = ComplaintStatusHistory(complaint_id=complaint_id, from_status=ComplaintStatus(doc["status"]), to_status=ComplaintStatus.REOPENED, changed_by=user.id, reason=data.reason)
        await self.db.complaint_status_history.insert_one(model_to_doc(history))
        await self.notifications.create_notification(doc["created_by"], "Complaint reopened", f"Complaint #{doc['public_id']} was reopened for review.", "complaint_reopened", complaint_id, {"remarks": data.reason, "status": ComplaintStatus.REOPENED.value})
        await AuditService(self.db).record(action="complaint.reopen", resource_type="complaint", resource_id=complaint_id, actor_id=user.id, details={"reason": data.reason})
        response = await self.get_by_id(complaint_id)
        return self._filter_internal_ai(response, user)

    async def add_comment(self, complaint_id: str, user: User, data: CommentCreate) -> CommentItem:
        doc = await self._get_doc(complaint_id)
        roles = set(user.roles)
        if data.is_internal and not roles.intersection({"admin", "officer", "field_staff"}):
            raise ForbiddenError("Only authorized staff can create internal comments")
        # Object-level authorization: the same read rules that gate
        # get_by_id_for_user also gate who may comment on a complaint.
        self._authorize_complaint_read(await self._to_response(doc), user)
        comment = ComplaintComment(complaint_id=complaint_id, user_id=user.id, content=data.comment.strip(), is_internal=data.is_internal)
        await self.db.complaint_comments.insert_one(model_to_doc(comment))
        if not data.is_internal and user.id == doc.get("created_by") and doc.get("assigned_staff_id"):
            await self.notifications.create_notification(doc["assigned_staff_id"], "Citizen commented", f"Comment on #{doc['public_id']}: {data.comment[:120]}", "mention", complaint_id, {"remarks": data.comment})
        elif not data.is_internal and user.id != doc.get("created_by"):
            await self.notifications.create_notification(doc["created_by"], "Official response", f"Update on #{doc['public_id']}: {data.comment[:120]}", "mention", complaint_id, {"remarks": data.comment})
        return CommentItem(id=comment.id, comment=comment.content, is_internal=comment.is_internal, author_id=user.id, author_name=user.full_name, author_role=next(iter(user.roles), "citizen"), created_at=comment.created_at)

    async def check_potential_duplicates(self, title: str, description: str, category_id: str, latitude: float | None = None, longitude: float | None = None) -> list[DuplicateCandidate]:
        category = await self.db.complaint_categories.find_one({"_id": category_id})
        candidates = await self.db.complaints.find({"deleted_at": None, "status": {"$nin": [ComplaintStatus.CLOSED.value, ComplaintStatus.REJECTED.value]}}).sort("created_at", -1).limit(30).to_list(length=30)
        enriched = []
        for doc in candidates:
            cat = await self.db.complaint_categories.find_one({"_id": doc.get("category_id")})
            enriched.append({"id": doc["_id"], "public_id": doc["public_id"], "title": doc["title"], "description": doc["description"], "category_slug": cat.get("slug") if cat else "", "category_name": cat.get("name") if cat else "", "status": doc["status"], "created_at": doc["created_at"], "latitude": doc.get("latitude"), "longitude": doc.get("longitude")})
        scored = await ai_client.check_duplicates(title, description, category.get("slug") if category else "other", latitude, longitude, enriched)
        return [DuplicateCandidate(id=item["id"], public_id=item["public_id"], title=item["title"], status=item["status"], category_name=item.get("category_name"), similarity_score=item["similarity_score"], distance_meters=item.get("distance_meters"), created_at=item["created_at"]) for item in scored]

    async def support_complaint(self, complaint_id: str, user: User) -> dict[str, Any]:
        """Let a nearby resident support an existing report instead of duplicating it."""
        doc = await self._get_doc(complaint_id)
        if doc.get("created_by") == user.id:
            raise ValidationError("The reporting citizen already owns this complaint")
        if user.id in (doc.get("supporters") or []):
            raise ValidationError("You have already supported this complaint")
        if doc.get("status") in {ComplaintStatus.CLOSED.value, ComplaintStatus.REJECTED.value}:
            raise ValidationError("Closed or rejected complaints cannot receive support")
        await self.db.complaints.update_one(
            {"_id": complaint_id},
            {"$addToSet": {"supporters": user.id}, "$inc": {"support_count": 1}, "$set": {"updated_at": utc_now()}},
        )
        await self.notifications.create_notification(
            doc["created_by"],
            "Neighbourhood support received",
            f"Another resident supported complaint #{doc['public_id']}.",
            "mention",
            complaint_id,
        )
        return {"complaint_id": complaint_id, "support_count": int(doc.get("support_count", 0)) + 1, "supported": True}

    async def nearby_complaints(self, latitude: float, longitude: float, radius_km: float = 2.0) -> list[ComplaintListItem]:
        docs = await self.db.complaints.find({
            "deleted_at": None,
            "status": {"$nin": [ComplaintStatus.CLOSED.value, ComplaintStatus.REJECTED.value]},
            "latitude": {"$ne": None},
            "longitude": {"$ne": None},
        }).sort("created_at", -1).limit(200).to_list(length=200)
        nearby: list[ComplaintListItem] = []
        for doc in docs:
            distance = _distance_km(latitude, longitude, doc.get("latitude"), doc.get("longitude"))
            if distance > radius_km:
                continue
            category = await self.db.complaint_categories.find_one({"_id": doc.get("category_id")})
            department = await self.db.departments.find_one({"_id": doc.get("assigned_department_id")}) if doc.get("assigned_department_id") else None
            staff = await self.db.users.find_one({"_id": doc.get("assigned_staff_id")}) if doc.get("assigned_staff_id") else None
            nearby.append(ComplaintListItem(
                id=doc["_id"], public_id=doc["public_id"], title=doc["title"],
                category_name=category.get("name") if category else None, category_slug=category.get("slug") if category else None,
                category_icon=category.get("icon") if category else None, priority=doc["priority"], status=doc["status"],
                address=doc.get("address"), latitude=doc.get("latitude"), longitude=doc.get("longitude"),
                created_at=doc["created_at"], updated_at=doc["updated_at"], creator_name=None,
                assigned_department_name=department.get("name") if department else None,
                assigned_staff_name=staff.get("full_name") if staff else None,
                media_count=await self.db.complaint_media.count_documents({"complaint_id": doc["_id"]}),
                requires_human_review=doc.get("requires_human_review", False), ai_is_mock=doc.get("ai_is_mock", False),
            ))
        return nearby

    async def _get_doc(self, complaint_id: str) -> dict[str, Any]:
        doc = await self.db.complaints.find_one({"_id": complaint_id, "deleted_at": None})
        if not doc:
            raise NotFoundError("Complaint not found")
        return doc

    async def _to_response(self, doc: dict[str, Any]) -> ComplaintResponse:
        category = await self.db.complaint_categories.find_one({"_id": doc.get("category_id")})
        department = await self.db.departments.find_one({"_id": doc.get("assigned_department_id")}) if doc.get("assigned_department_id") else None
        creator = await self.db.users.find_one({"_id": doc.get("created_by")})
        staff = await self.db.users.find_one({"_id": doc.get("assigned_staff_id")}) if doc.get("assigned_staff_id") else None
        media = await self.db.complaint_media.find({"complaint_id": doc["_id"]}).sort("created_at", 1).to_list(length=100)
        histories = await self.db.complaint_status_history.find({"complaint_id": doc["_id"]}).sort("created_at", 1).to_list(length=100)
        comments = await self.db.complaint_comments.find({"complaint_id": doc["_id"]}).sort("created_at", 1).to_list(length=200)
        verifications = await self.db.complaint_verifications.find({"complaint_id": doc["_id"]}).sort("created_at", 1).to_list(length=50)
        return ComplaintResponse(
            id=doc["_id"], public_id=doc["public_id"], title=doc["title"], description=doc["description"], category_id=doc["category_id"],
            category=CategoryResponse(id=category["_id"], name=category["name"], slug=category["slug"], description=category.get("description"), icon=category.get("icon"), color=category.get("color"), department_id=category.get("department_id"), department_name=department.get("name") if department and category.get("department_id") == department.get("_id") else None, is_active=category.get("is_active", True), display_order=category.get("display_order", 0)) if category else None,
            priority=doc["priority"], status=doc["status"], latitude=doc.get("latitude"), longitude=doc.get("longitude"), address=doc.get("address"), landmark=doc.get("landmark"),
            state=doc.get("state"), district=doc.get("district"), city=doc.get("city"), locality=doc.get("locality"),
            sub_district=doc.get("sub_district"), block=doc.get("block"), gram_panchayat=doc.get("gram_panchayat"), ward=doc.get("ward"),
            pincode=doc.get("pincode"), original_language=doc.get("original_language", "en"), created_by=doc["created_by"],
            creator=await self._brief(creator) if creator else None, assigned_department_id=doc.get("assigned_department_id"),
            assigned_department=DepartmentResponse(id=department["_id"], name=department["name"], code=department["code"], description=department.get("description"), contact_email=department.get("contact_email"), contact_phone=department.get("contact_phone"), is_active=department.get("is_active", True), created_at=department.get("created_at")) if department else None,
            assigned_staff_id=doc.get("assigned_staff_id"), assigned_staff=await self._brief(staff) if staff else None, ai_category=doc.get("ai_category"), ai_confidence=doc.get("ai_confidence"), ai_is_mock=doc.get("ai_is_mock", False), requires_human_review=doc.get("requires_human_review", not doc.get("ai_category") or doc.get("ai_confidence", 0) < 0.5), ai_outcome=doc.get("ai_outcome", "human_review"), ai_reason=doc.get("ai_reason"), ai_model_version=doc.get("ai_model_version"), ai_verified_at=doc.get("ai_verified_at"), ai_verification=doc.get("ai_verification") or {},
            duplicate_group_id=doc.get("duplicate_group_id"), duplicate_score=doc.get("duplicate_score"), voice_description_url=doc.get("voice_description_url"), resolution_notes=doc.get("resolution_notes"),
            media=[MediaItem(id=item["_id"], media_type=item.get("media_type", "image"), media_url=signed_media_url(item["file_url"]), file_name=item.get("file_name"), is_resolution_proof=item.get("is_resolution_evidence", False), evidence_stage=item.get("evidence_stage"), uploaded_at=item.get("created_at")) for item in media],
            comments=[CommentItem(id=item["_id"], comment=item["content"], is_internal=item.get("is_internal", False), author_id=item["user_id"], author_name=await self._user_name(item["user_id"]), author_role=await self._user_role(item["user_id"]), created_at=item["created_at"]) for item in comments],
            status_history=[StatusHistoryItem(id=item["_id"], old_status=item.get("from_status"), new_status=item["to_status"], changed_by_id=item["changed_by"], changed_by_name=await self._user_name(item["changed_by"]), notes=item.get("reason"), created_at=item["created_at"]) for item in histories],
            verifications=[VerificationItem(id=item["_id"], action=item["action"], feedback=item.get("reason"), rating=item.get("rating"), verified_by_id=item["verified_by"], verified_by_name=await self._user_name(item["verified_by"]), created_at=item["created_at"]) for item in verifications],
            created_at=doc["created_at"], updated_at=doc["updated_at"], resolved_at=doc.get("resolved_at"), closed_at=doc.get("closed_at"), resolution_deadline=doc.get("resolution_deadline"), resolution_submitted_at=doc.get("resolution_submitted_at"), is_overdue=bool(doc.get("is_overdue", False)), escalation_level=int(doc.get("escalation_level", 0)),
        )

    async def _brief(self, doc: dict[str, Any]) -> UserBrief:
        department = await self.db.departments.find_one({"_id": doc.get("department_id")}) if doc.get("department_id") else None
        return UserBrief(id=doc["_id"], email=doc["email"], full_name=doc["full_name"], phone=doc.get("phone"), avatar_url=doc.get("avatar_url"), roles=doc.get("roles", []), department_id=doc.get("department_id"), department_name=department.get("name") if department else None, city=doc.get("city"), is_active=doc.get("is_active", True), is_verified=doc.get("is_verified", False), email_verified=doc.get("email_verified", False), mobile_verified=doc.get("mobile_verified", False), identity_verified=doc.get("identity_verified", False))

    async def _user_name(self, user_id: str | None) -> str | None:
        if not user_id:
            return None
        doc = await self.db.users.find_one({"_id": user_id}, {"full_name": 1})
        return doc.get("full_name") if doc else None

    async def _user_role(self, user_id: str | None) -> str | None:
        if not user_id:
            return None
        doc = await self.db.users.find_one({"_id": user_id}, {"roles": 1})
        return doc.get("roles", ["citizen"])[0] if doc else None


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    lat_delta = radians(lat2 - lat1)
    lon_delta = radians(lon2 - lon1)
    value = sin(lat_delta / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(lon_delta / 2) ** 2
    return radius * 2 * asin(sqrt(value))
