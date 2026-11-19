"""
CivicLens AI Service — FastAPI Application

Provides AI-powered classification and duplicate detection.
Real provider mode is configured through ``ai_service/.env``; set
``AI_MOCK_MODE=true`` only for explicitly isolated local tests.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import httpx
import structlog
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.mock_provider import mock_provider
from app.provider_registry import build_provider
from app.schemas import (
    ComplaintVerificationResult,
    DuplicateDetectionResult,
    ImageClassificationResult,
    SpamCheckResult,
    TextClassificationResult,
)
from app.settings import AISettings

logger = structlog.get_logger()
settings = AISettings()
provider = build_provider(settings)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    mode = "MOCK" if settings.AI_MOCK_MODE else settings.AI_PROVIDER.upper()
    logger.info("ai_service.startup", mode=mode)
    yield
    logger.info("ai_service.shutdown")


app = FastAPI(
    title="CivicLens AI Service",
    description="AI classification, duplicate detection, and spam analysis for civic complaints.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "CivicLens AI Service",
        "version": "1.0.0",
        "mock_mode": settings.AI_MOCK_MODE,
        "provider": "mock" if settings.AI_MOCK_MODE else settings.AI_PROVIDER,
    }


@app.post("/classify-image", response_model=ImageClassificationResult, tags=["Classification"])
async def classify_image(file: Annotated[UploadFile, File(...)]) -> ImageClassificationResult | JSONResponse:
    logger.info("ai.classify_image", filename=file.filename, mock=settings.AI_MOCK_MODE)

    if settings.AI_MOCK_MODE:
        result = mock_provider.classify_image(filename=file.filename)
        result.model_version = settings.AI_MODEL_VERSION
        return result

    content = await file.read()
    mime = file.content_type or "image/jpeg"
    try:
        result = await provider.classify_image(  # type: ignore[union-attr]
            filename=file.filename,
            content=content,
            mime_type=mime,
        )
        result.model_version = settings.AI_MODEL_VERSION
        return result
    except httpx.HTTPError as exc:
        logger.error(
            "ai.classify_image.provider_error",
            error_type=type(exc).__name__,
            error=str(exc) or type(exc).__name__,
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": "AI classification temporarily unavailable",
                "category": "other",
                "confidence": None,
                "confidence_status": "unavailable",
                "is_mock": False,
                "is_relevant": False,
                "requires_human_review": True,
            },
        )


@app.post("/verify-complaint", response_model=ComplaintVerificationResult, tags=["Verification"])
async def verify_complaint(
    title: str = Form(...),
    description: str = Form(...),
    selected_category: str = Form(...),
    files: Annotated[list[UploadFile] | None, File()] = None,
) -> ComplaintVerificationResult | JSONResponse:
    """Run advisory text and evidence verification for a complaint submission."""
    files = files or []
    logger.info(
        "ai.verify_complaint",
        title_length=len(title),
        description_length=len(description),
        evidence_count=len(files),
        mock=settings.AI_MOCK_MODE,
    )
    if settings.AI_MOCK_MODE:
        text = mock_provider.classify_text(f"{title}. {description}")
        return ComplaintVerificationResult(
            text=text,
            selected_category=selected_category,
            category_match=text.category == selected_category and text.is_relevant,
            category_match_confidence=text.confidence if text.category == selected_category else 0.0,
            severity=text.suggested_priority,
            confidence=text.confidence,
            requires_human_review=True,
            is_mock=True,
            limitations=[
                "Mock mode does not inspect evidence pixels or video frames.",
                "AI output is advisory and cannot conclusively prove authenticity or manipulation.",
            ],
            model_version=settings.AI_MODEL_VERSION,
        )

    evidence: list[tuple[str | None, bytes, str]] = []
    try:
        for file in files:
            content = await file.read()
            mime_type = file.content_type or "application/octet-stream"
            if mime_type.startswith("video/"):
                frame = _extract_video_frame(content, file.filename)
                if frame is not None:
                    evidence.append((f"{file.filename or 'video'}.frame.jpg", frame, "image/jpeg"))
                else:
                    evidence.append((file.filename, content, mime_type))
            else:
                evidence.append((file.filename, content, mime_type))
        result = await provider.verify_complaint(  # type: ignore[union-attr]
            title=title,
            description=description,
            selected_category=selected_category,
            evidence=evidence,
        )
        if files and any((file.content_type or "").startswith("video/") for file in files):
            for evidence_result in result.evidence:
                if evidence_result.media_type == "image":
                    evidence_result.media_type = "video"
                    evidence_result.requires_human_review = True
                    evidence_result.message = (evidence_result.message or "") + " Only a sampled video frame was reviewed; inspect the full video manually."
            result.requires_human_review = True
            result.limitations.append("Video analysis reviewed a sampled frame only; an officer must inspect the full recording.")
        result.model_version = settings.AI_MODEL_VERSION
        return result
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        logger.error("ai.verify_complaint.provider_error", error=str(exc))
        return JSONResponse(
            status_code=503,
            content={"detail": "AI verification temporarily unavailable"},
        )


@app.post("/classify-text", response_model=TextClassificationResult, tags=["Classification"])
async def classify_text(text: str = Form(...)) -> TextClassificationResult | JSONResponse:
    logger.info("ai.classify_text", text_length=len(text), mock=settings.AI_MOCK_MODE)

    if settings.AI_MOCK_MODE:
        result = mock_provider.classify_text(text)
        result.model_version = settings.AI_MODEL_VERSION
        return result

    try:
        result = await provider.classify_text(text)  # type: ignore[union-attr]
        result.model_version = settings.AI_MODEL_VERSION
        return result
    except httpx.HTTPError as exc:
        logger.error(
            "ai.classify_text.provider_error",
            error_type=type(exc).__name__,
            error=str(exc) or type(exc).__name__,
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": "AI classification temporarily unavailable",
                "confidence": None,
                "confidence_status": "unavailable",
                "requires_human_review": True,
            },
        )


@app.post("/check-spam", response_model=SpamCheckResult, tags=["Moderation"])
async def check_spam(
    text: str = Form(...),
    user_submission_count: int = Form(default=0),
) -> SpamCheckResult | JSONResponse:
    logger.info("ai.check_spam", text_length=len(text), mock=settings.AI_MOCK_MODE)
    if settings.AI_MOCK_MODE:
        return mock_provider.check_spam(text, user_submission_count)
    try:
        return await provider.check_spam(text, user_submission_count)  # type: ignore[union-attr]
    except httpx.HTTPError as exc:
        logger.error("ai.check_spam.provider_error", error=str(exc))
        return JSONResponse(status_code=503, content={"detail": "Spam check temporarily unavailable"})


@app.post("/find-duplicates", response_model=DuplicateDetectionResult, tags=["Duplicates"])
async def find_duplicates(
    text: str = Form(...),
    category: str = Form(default=""),
    latitude: float = Form(default=0.0),
    longitude: float = Form(default=0.0),
) -> DuplicateDetectionResult:
    logger.info(
        "ai.find_duplicates",
        text_length=len(text),
        category=category,
        mock=settings.AI_MOCK_MODE,
    )
    if settings.AI_MOCK_MODE:
        return mock_provider.find_duplicates(text, category, latitude, longitude)
    return await provider.find_duplicates(text, category, latitude, longitude)  # type: ignore[union-attr]


def _extract_video_frame(content: bytes, filename: str | None) -> bytes | None:
    """Extract one frame when the optional OpenCV dependency is installed."""
    try:
        import cv2
    except ImportError:
        return None
    suffix = os.path.splitext(filename or "video.mp4")[1] or ".mp4"
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            handle.write(content)
            path = handle.name
        capture = cv2.VideoCapture(path)
        success, frame = capture.read()
        capture.release()
        if not success:
            return None
        success, encoded = cv2.imencode(".jpg", frame)
        return encoded.tobytes() if success else None
    finally:
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass
