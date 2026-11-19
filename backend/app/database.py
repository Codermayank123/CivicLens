"""
CivicLens Backend — MongoDB Database Engine & Connection Management

Uses Motor (official async MongoDB driver) for high-performance non-blocking
database operations. Exposes get_db dependency and automatic index creation.
"""

from __future__ import annotations

from typing import AsyncGenerator
import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, GEOSPHERE, IndexModel

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

_mongo_client: AsyncIOMotorClient | None = None
_mongo_db: AsyncIOMotorDatabase | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    """Return the global Motor client, creating it if needed."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=15000,
            retryWrites=True,
            retryReads=True,
        )
    return _mongo_client


def get_database() -> AsyncIOMotorDatabase:
    """Return the global Motor database instance."""
    global _mongo_db
    if _mongo_db is None:
        client = get_mongo_client()
        _mongo_db = client[settings.MONGODB_DB_NAME]
    return _mongo_db


def set_database(db: AsyncIOMotorDatabase) -> None:
    """Override database instance (used for testing and in-memory mocks)."""
    global _mongo_db
    _mongo_db = db


async def init_db() -> None:
    """Initialize MongoDB connection and ensure all collections and indexes exist."""
    db = get_database()
    # Do not place connection strings, hosts, usernames, or query parameters
    # in logs. Configuration diagnostics report only that a target is set.
    logger.info("mongodb.connecting", target_configured=bool(settings.MONGODB_URL), db=settings.MONGODB_DB_NAME)
    try:
        await db.command("ping")
        logger.info("mongodb.ping_success")
    except Exception as exc:
        # Never start a process that can later claim writes succeeded while its
        # configured Atlas database is unavailable.
        logger.error("mongodb.ping_failed", error=type(exc).__name__)
        raise RuntimeError("Configured MongoDB database is unavailable") from exc

    await create_indexes(db)


async def close_db() -> None:
    """Close MongoDB connections on shutdown."""
    global _mongo_client, _mongo_db
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
        _mongo_db = None
        logger.info("mongodb.closed")


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create all required unique, compound, and geospatial indexes."""
    try:
        # Users collection
        await db.users.create_indexes([
            IndexModel([("email", ASCENDING)], unique=True, name="uniq_user_email"),
            IndexModel([("phone", ASCENDING)], unique=True, sparse=True, name="uniq_user_phone"),
            IndexModel([("department_id", ASCENDING)], name="idx_user_dept"),
            IndexModel([("roles", ASCENDING)], name="idx_user_roles"),
            IndexModel([("is_active", ASCENDING)], name="idx_user_active"),
            IndexModel([("civic_points", DESCENDING)], name="idx_user_points"),
        ])

        # Refresh tokens collection
        await db.refresh_tokens.create_indexes([
            IndexModel([("token_hash", ASCENDING)], unique=True, name="uniq_token_hash"),
            IndexModel([("user_id", ASCENDING)], name="idx_token_user"),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_token_expiry"),
        ])

        # Phone OTP challenges are hashed, short-lived, and single-use.
        await db.otp_challenges.create_indexes([
            IndexModel([("user_id", ASCENDING), ("purpose", ASCENDING), ("created_at", DESCENDING)], name="idx_otp_user_purpose"),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_otp_expiry"),
        ])

        # Registration OTP sessions contain only hashes and expire automatically.
        await db.registration_verifications.create_indexes([
            IndexModel([("email", ASCENDING), ("created_at", DESCENDING)], name="idx_registration_email"),
            IndexModel([("session_token_hash", ASCENDING)], unique=True, name="uniq_registration_session_token"),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_registration_expiry"),
        ])

        # Departments collection
        await db.departments.create_indexes([
            IndexModel([("code", ASCENDING)], unique=True, name="uniq_dept_code"),
            IndexModel([("name", ASCENDING)], unique=True, name="uniq_dept_name"),
        ])

        # Complaint categories collection
        await db.complaint_categories.create_indexes([
            IndexModel([("slug", ASCENDING)], unique=True, name="uniq_cat_slug"),
            IndexModel([("department_id", ASCENDING)], name="idx_cat_dept"),
        ])

        # Complaints collection (Geospatial 2dsphere index)
        await db.complaints.create_indexes([
            IndexModel([("public_id", ASCENDING)], unique=True, name="uniq_complaint_public_id"),
            IndexModel([("location", GEOSPHERE)], name="idx_complaint_geo"),
            IndexModel([("status", ASCENDING)], name="idx_complaint_status"),
            IndexModel([("priority", ASCENDING)], name="idx_complaint_priority"),
            IndexModel([("category_id", ASCENDING)], name="idx_complaint_cat"),
            IndexModel([("assigned_department_id", ASCENDING)], name="idx_complaint_dept"),
            IndexModel([("assigned_staff_id", ASCENDING)], name="idx_complaint_staff"),
            IndexModel([("created_by", ASCENDING)], name="idx_complaint_creator"),
            IndexModel([("created_at", DESCENDING)], name="idx_complaint_created"),
            IndexModel([("ai_outcome", ASCENDING), ("requires_human_review", ASCENDING), ("created_at", DESCENDING)], name="idx_complaint_ai_review"),
            IndexModel([("resolution_deadline", ASCENDING), ("is_overdue", ASCENDING)], name="idx_complaint_deadline"),
            IndexModel([("state", ASCENDING), ("district", ASCENDING), ("status", ASCENDING)], name="idx_complaint_geo_admin"),
        ])

        # Complaint media
        await db.complaint_media.create_indexes([
            IndexModel([("complaint_id", ASCENDING)], name="idx_media_complaint"),
            IndexModel([("complaint_id", ASCENDING), ("is_resolution_evidence", ASCENDING), ("evidence_stage", ASCENDING)], name="idx_media_resolution_stage"),
            IndexModel([("sha256", ASCENDING)], sparse=True, name="idx_media_hash"),
        ])

        # Complaint status history
        await db.complaint_status_history.create_indexes([
            IndexModel([("complaint_id", ASCENDING), ("created_at", DESCENDING)], name="idx_status_hist_complaint"),
        ])

        await db.complaint_assignments.create_indexes([
            IndexModel([("complaint_id", ASCENDING), ("created_at", DESCENDING)], name="idx_assignment_complaint"),
            IndexModel([("assigned_to", ASCENDING), ("created_at", DESCENDING)], name="idx_assignment_staff"),
        ])

        # Complaint comments
        await db.complaint_comments.create_indexes([
            IndexModel([("complaint_id", ASCENDING), ("created_at", DESCENDING)], name="idx_comment_complaint"),
        ])

        # Complaint verifications
        await db.complaint_verifications.create_indexes([
            IndexModel([("complaint_id", ASCENDING)], name="idx_verif_complaint"),
            IndexModel([("verified_by", ASCENDING)], name="idx_verif_user"),
        ])

        await db.complaint_duplicates.create_indexes([
            IndexModel([("complaint_id", ASCENDING)], name="idx_duplicate_complaint"),
            IndexModel([("confirmed", ASCENDING)], name="idx_duplicate_confirmed"),
        ])

        await db.ai_predictions.create_indexes([
            IndexModel([("complaint_id", ASCENDING), ("prediction_type", ASCENDING)], name="idx_ai_prediction_complaint"),
        ])

        # Conversations & Messages (Real-time Messaging)
        await db.conversations.create_indexes([
            IndexModel([("complaint_id", ASCENDING)], name="idx_conv_complaint"),
            IndexModel([("participant_ids", ASCENDING)], name="idx_conv_participants"),
        ])
        await db.messages.create_indexes([
            IndexModel([("conversation_id", ASCENDING), ("created_at", ASCENDING)], name="idx_msg_conv"),
            IndexModel([("complaint_id", ASCENDING)], name="idx_msg_complaint"),
        ])

        # Notifications
        await db.notifications.create_indexes([
            IndexModel([("user_id", ASCENDING), ("is_read", ASCENDING)], name="idx_notif_user_unread"),
            IndexModel([("created_at", DESCENDING)], name="idx_notif_created"),
            IndexModel([("dedupe_key", ASCENDING)], unique=True, sparse=True, name="uniq_notif_dedupe"),
        ])

        # Rewards and points transactions
        await db.points_transactions.create_indexes([
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)], name="idx_points_user"),
            IndexModel([("action_type", ASCENDING)], name="idx_points_action"),
            IndexModel([("user_id", ASCENDING), ("action_type", ASCENDING), ("reference_id", ASCENDING)], unique=True, sparse=True, name="uniq_points_reference"),
        ])

        # Community challenges
        await db.community_challenges.create_indexes([
            IndexModel([("is_active", ASCENDING)], name="idx_challenge_active"),
            IndexModel([("start_date", ASCENDING), ("end_date", ASCENDING)], name="idx_challenge_dates"),
        ])
        await db.challenge_participations.create_indexes([
            IndexModel([("challenge_id", ASCENDING), ("user_id", ASCENDING)], unique=True, name="uniq_challenge_participant"),
            IndexModel([("user_id", ASCENDING)], name="idx_challenge_user"),
        ])
        await db.challenge_submissions.create_indexes([
            IndexModel([("challenge_id", ASCENDING), ("user_id", ASCENDING)], name="idx_challenge_submission"),
            IndexModel([("status", ASCENDING)], name="idx_challenge_submission_status"),
        ])
        await db.certificates.create_indexes([
            IndexModel([("user_id", ASCENDING), ("issued_at", DESCENDING)], name="idx_certificate_user"),
            IndexModel([("certificate_hash", ASCENDING)], unique=True, name="uniq_certificate_hash"),
        ])

        # Identity verification sessions
        await db.identity_verification_sessions.create_indexes([
            IndexModel([("user_id", ASCENDING)], name="idx_id_user"),
            IndexModel([("status", ASCENDING)], name="idx_id_status"),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0, name="ttl_id_expiry"),
        ])

        # Audit logs
        await db.audit_logs.create_indexes([
            IndexModel([("actor_id", ASCENDING)], name="idx_audit_actor"),
            IndexModel([("action", ASCENDING)], name="idx_audit_action"),
            IndexModel([("created_at", DESCENDING)], name="idx_audit_created"),
        ])

        await db.complaint_escalations.create_indexes([
            IndexModel([("complaint_id", ASCENDING), ("created_at", DESCENDING)], name="idx_escalation_complaint"),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)], name="idx_escalation_status"),
        ])

        await db.notification_deliveries.create_indexes([
            IndexModel([("notification_id", ASCENDING)], name="idx_delivery_notification"),
            IndexModel([("notification_id", ASCENDING), ("channel", ASCENDING)], unique=True, name="uniq_delivery_channel"),
            IndexModel([("status", ASCENDING), ("next_attempt_at", ASCENDING)], name="idx_delivery_retry"),
        ])

        logger.info("mongodb.indexes_ensured")
    except Exception as exc:
        logger.error("mongodb.create_indexes_failed", error=type(exc).__name__)
        raise RuntimeError("MongoDB index initialization failed") from exc


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """FastAPI dependency providing MongoDB database instance per request."""
    db = get_database()
    yield db
