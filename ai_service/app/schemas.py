from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ImageClassificationResult(BaseModel):
    category: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_status: str = "unavailable"
    department: str | None = None
    is_mock: bool = False
    is_relevant: bool = False
    message: str | None = None
    top_predictions: list[dict[str, Any]] = Field(default_factory=list)
    evidence_quality: str = "unknown"
    authenticity_indicators: list[str] = Field(default_factory=list)
    manipulation_indicators: list[str] = Field(default_factory=list)
    suspicious: bool = False
    requires_human_review: bool = True
    media_type: str = "image"
    model_version: str = "unknown"


class TextClassificationResult(BaseModel):
    category: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_status: str = "unavailable"
    department: str | None = None
    keywords: list[str] = Field(default_factory=list)
    urgency: str = "medium"
    suggested_priority: str = "medium"
    is_mock: bool = False
    is_relevant: bool = False
    message: str | None = None
    model_version: str = "unknown"


class DuplicateCandidate(BaseModel):
    complaint_id: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    text_similarity: float = 0.0
    geo_distance_km: float = 0.0
    category_match: bool = False


class DuplicateDetectionResult(BaseModel):
    duplicates: list[DuplicateCandidate] = Field(default_factory=list)
    is_mock: bool = False


class SpamCheckResult(BaseModel):
    is_spam: bool = False
    spam_score: float = Field(ge=0.0, le=1.0, default=0.0)
    reasons: list[str] = Field(default_factory=list)
    is_mock: bool = False


class ComplaintVerificationResult(BaseModel):
    """Advisory verification output; it never asserts that evidence is genuine."""

    text: TextClassificationResult
    evidence: list[ImageClassificationResult] = Field(default_factory=list)
    selected_category: str
    category_match: bool = False
    category_match_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    severity: str = "medium"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_status: str = "unavailable"
    suspicious: bool = False
    suspicious_reasons: list[str] = Field(default_factory=list)
    requires_human_review: bool = True
    is_mock: bool = False
    limitations: list[str] = Field(default_factory=list)
    model_version: str = "unknown"
