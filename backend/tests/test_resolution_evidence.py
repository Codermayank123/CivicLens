import pytest

from app.core.mongo import model_to_doc
from app.models.complaint import Complaint, ComplaintStatus
from app.models.user import User
from app.schemas.complaint import ResolutionEvidence, StatusUpdate
from app.services.complaint_service import ComplaintService


@pytest.mark.asyncio
async def test_resolution_requires_remarks_and_stored_photos(db_session, demo_user, demo_category, monkeypatch):
    complaint = Complaint(
        public_id="POT-123456",
        title="Stored pothole",
        description="A deep pothole is blocking traffic.",
        category_id=demo_category.id,
        created_by=demo_user.id,
        assigned_department_id=demo_category.department_id,
        assigned_staff_id="field-1",
        status=ComplaintStatus.IN_PROGRESS,
    )
    await db_session.complaints.insert_one(model_to_doc(complaint))
    officer = User(
        id="field-1",
        email="field@example.com",
        full_name="Field Officer",
        password_hash="hash",
        roles=["field_staff"],
        department_id=demo_category.department_id,
        is_verified=True,
        identity_verified=True,
    )
    service = ComplaintService(db_session)
    await db_session.users.insert_one(model_to_doc(officer))

    missing = await _run_status(service, complaint.id, officer, StatusUpdate(status=ComplaintStatus.RESOLVED, notes=""))
    assert missing == "Resolution remarks are required before resolving a complaint"

    async def missing_file(url: str):
        return None

    monkeypatch.setattr("app.services.complaint_service.storage_service.read_file_url", missing_file)
    failed_upload = await _run_status(
        service,
        complaint.id,
        officer,
        StatusUpdate(
            status=ComplaintStatus.RESOLVED,
            notes="Attempted repair.",
            resolution_evidence=[
                ResolutionEvidence(media_url="/uploads/complaints/0123456789abcdef0123456789abcdef.jpg", stage="before"),
                ResolutionEvidence(media_url="/uploads/complaints/fedcba9876543210fedcba9876543210.jpg", stage="after"),
            ],
        ),
    )
    assert failed_upload == "Every resolution photograph must be stored before the status is updated"
    stored_complaint = await db_session.complaints.find_one({"_id": complaint.id})
    assert stored_complaint["status"] == ComplaintStatus.IN_PROGRESS.value

    async def stored_file(url: str):
        return b"\xff\xd8\xffphoto-bytes"

    monkeypatch.setattr("app.services.complaint_service.storage_service.read_file_url", stored_file)
    result = await service.update_status(
        complaint.id,
        officer,
        StatusUpdate(
            status=ComplaintStatus.RESOLVED,
            notes="Road surface repaired and inspected.",
            resolution_evidence=[
                ResolutionEvidence(media_url="/uploads/complaints/0123456789abcdef0123456789abcdef.jpg", stage="before"),
                ResolutionEvidence(media_url="/uploads/complaints/fedcba9876543210fedcba9876543210.jpg", stage="after"),
            ],
        ),
    )
    assert result.status == ComplaintStatus.CITIZEN_VERIFICATION_PENDING
    assert await db_session.complaint_media.count_documents({"complaint_id": complaint.id, "is_resolution_evidence": True}) == 2


async def _run_status(service, complaint_id, user, data):
    try:
        await service.update_status(complaint_id, user, data)
    except Exception as exc:
        return str(exc)
    return None
