import pytest

from app.core.mongo import model_to_doc
from app.email.providers.mock import clear_mock_outbox, sent_messages
from app.models.complaint import Complaint, ComplaintMedia, ComplaintStatus, MediaType
from app.models.department import Department
from app.models.user import User
from app.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_resolution_email_attaches_multiple_photos_and_is_idempotent(db_session, monkeypatch):
    clear_mock_outbox()
    user = User(email="notify@example.com", full_name="Notify Citizen", password_hash="hash", is_verified=True)
    department = Department(name="Public Works", code="PUBLIC-WORKS")
    complaint = Complaint(
        public_id="POT-555555",
        title="Resolved complaint",
        description="A resolved road issue.",
        category_id="category",
        created_by=user.id,
        assigned_department_id=department.id,
        status=ComplaintStatus.RESOLVED,
    )
    await db_session.users.insert_one(model_to_doc(user))
    await db_session.departments.insert_one(model_to_doc(department))
    await db_session.complaints.insert_one(model_to_doc(complaint))
    for name in ("after-one.jpg", "after-two.jpg"):
        await db_session.complaint_media.insert_one(model_to_doc(ComplaintMedia(
            complaint_id=complaint.id,
            media_type=MediaType.IMAGE,
            file_url=f"/uploads/complaints/{name.replace('-', '')[:32]}.jpg",
            file_name=name,
            file_size=10,
            mime_type="image/jpeg",
            is_resolution_evidence=True,
            evidence_stage="after",
            uploaded_by="officer",
        )))

    async def read_file_url(file_url: str):
        return b"photo-bytes"

    monkeypatch.setattr("app.services.notification_service.storage_service.read_file_url", read_file_url)
    service = NotificationService(db_session)
    data = {"resolution": True, "remarks": "Repairs completed."}
    await service.create_notification(user.id, "Complaint resolved", "Repairs completed.", "complaint_resolved", complaint.id, data)
    await service.create_notification(user.id, "Complaint resolved", "Repairs completed.", "complaint_resolved", complaint.id, data)

    assert len(sent_messages) == 1
    assert len(sent_messages[0].attachments) == 2
    assert await db_session.notifications.count_documents({"complaint_id": complaint.id}) == 1
    assert await db_session.notification_deliveries.count_documents({"channel": "email", "status": "accepted"}) == 1


@pytest.mark.asyncio
async def test_email_provider_failure_is_recorded_without_claiming_delivery(db_session, monkeypatch):
    user = User(email="failure@example.com", full_name="Failure Citizen", password_hash="hash", is_verified=True)
    await db_session.users.insert_one(model_to_doc(user))

    class FailingEmail:
        async def send(self, **kwargs):
            raise RuntimeError("provider failure")

        async def send_complaint_update(self, **kwargs):
            raise RuntimeError("provider failure")

    monkeypatch.setattr("app.services.notification_service.get_email_service", lambda: FailingEmail())
    await NotificationService(db_session).create_notification(user.id, "Status update", "Status changed.", "status_update")
    delivery = await db_session.notification_deliveries.find_one({"channel": "email"})
    assert delivery["status"] == "failed"
    assert delivery["error"] == "RuntimeError"
