"""
CivicLens — AI Service Client
Interfaces with the AI microservice for text/image classification, duplicate detection, and spam checking.
Provider failures are explicit and routed to human review; no synthetic AI
classification is returned.
"""

from __future__ import annotations

import re
from math import asin, cos, radians, sin, sqrt
from pathlib import PurePosixPath
from typing import Any

import httpx
import structlog

from app.config import get_settings
from app.exceptions import AIServiceError
from app.services.storage_service import storage_service

logger = structlog.get_logger()
settings = get_settings()


class AIClient:
    def __init__(self):
        self.ai_url = getattr(settings, "AI_SERVICE_URL", "http://localhost:8001")

    @property
    def _timeout(self) -> float:
        return float(getattr(settings, "AI_CLIENT_TIMEOUT_SECONDS", 60.0) or 60.0)

    async def classify_text(self, text: str) -> dict[str, Any]:
        """Classify text through the AI service, failing closed when unavailable."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.post(f"{self.ai_url}/classify-text", data={"text": text})
                if res.status_code == 200:
                    payload = res.json()
                    payload.setdefault("is_relevant", payload.get("category") != "other")
                    payload.setdefault("is_mock", False)
                    if payload.get("confidence") is not None:
                        payload.setdefault("confidence_status", "available")
                    else:
                        payload.setdefault("confidence_status", "unavailable")
                    return payload
                logger.warning("ai_client.text_classification_unavailable", status=res.status_code)
                if settings.is_production:
                    raise AIServiceError()
        except Exception as exc:
            logger.warning("ai_client.text_classification_unavailable", error=type(exc).__name__)
            if settings.is_production:
                if isinstance(exc, AIServiceError):
                    raise
                raise AIServiceError() from exc

        # A provider outage is not a classification. Keep the complaint safe
        # and route it to human review instead of fabricating an AI result.
        return {
            "category": "other",
            "confidence": None,
            "confidence_status": "unavailable",
            "urgency": "medium",
            "suggested_priority": "medium",
            "is_mock": False,
            "is_relevant": False,
            "provider_unavailable": True,
            "requires_human_review": True,
            "message": "AI analysis is temporarily unavailable; your complaint has been queued for human review.",
        }

    async def verify_complaint(
        self,
        *,
        title: str,
        description: str,
        selected_category: str,
        media_urls: list[str],
    ) -> dict[str, Any]:
        """Run advisory text and evidence verification through the AI service.

        Evidence is read from managed storage and sent only to the configured AI
        service. Provider failures are represented explicitly and routed to
        human review; no synthetic result is returned.
        """
        files: list[tuple[str, bytes, str]] = []
        for url in media_urls:
            filename = PurePosixPath(url).name
            content = await storage_service.read_managed_file(filename)
            if content is not None:
                mime_type = "video/mp4" if filename.lower().endswith(".mp4") else "image/jpeg"
                if filename.lower().endswith(".png"):
                    mime_type = "image/png"
                elif filename.lower().endswith(".webp"):
                    mime_type = "image/webp"
                elif filename.lower().endswith(".jpeg"):
                    mime_type = "image/jpeg"
                files.append((filename, content, mime_type))

        if not media_urls:
            text = await self.classify_text(f"Selected category: {selected_category}. {title}. {description}")
            category_match = text.get("category") == selected_category and bool(text.get("is_relevant", False))
            return {
                "text": text,
                "evidence": [],
                "selected_category": selected_category,
                "category_match": category_match,
                "category_match_confidence": text.get("confidence") if category_match else None,
                "severity": text.get("suggested_priority", "medium"),
                "confidence": text.get("confidence"),
                "confidence_status": text.get("confidence_status", "unavailable"),
                "suspicious": False,
                "suspicious_reasons": [],
                "requires_human_review": not category_match or text.get("confidence") is None or text.get("confidence", 0.0) < 0.5,
                "is_mock": bool(text.get("is_mock", False)),
                "limitations": [
                    "AI output is advisory and cannot conclusively prove authenticity, intent, or manipulation.",
                    "Uncertain cases must be reviewed by an authorized officer.",
                ],
            }

        try:
            form_files = [("files", (name, content, mime)) for name, content, mime in files]
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.post(
                    f"{self.ai_url}/verify-complaint",
                    data={
                        "title": title,
                        "description": description,
                        "selected_category": selected_category,
                    },
                    files=form_files,
                )
            if res.status_code == 200:
                return res.json()
            if settings.is_production:
                raise AIServiceError()
            logger.warning("ai_client.complaint_verification_unavailable", status=res.status_code)
        except Exception as exc:
            logger.warning("ai_client.complaint_verification_fallback", error=str(exc))
            if settings.is_production:
                raise AIServiceError() from exc

        text = await self.classify_text(f"Selected category: {selected_category}. {title}. {description}")
        evidence = [
            {
                "category": "other",
                "confidence": None,
                "confidence_status": "unavailable",
                "is_mock": False,
                "is_relevant": False,
                "message": "Evidence pixels/video frames were not analyzed because the AI service was unavailable.",
                "evidence_quality": "unknown",
                "authenticity_indicators": [],
                "manipulation_indicators": [],
                "suspicious": False,
                "requires_human_review": True,
                "media_type": "video" if mime == "video/mp4" else "image",
                "top_predictions": [],
            }
            for _, _, mime in files
        ]
        category_match = text.get("category") == selected_category and bool(text.get("is_relevant", False))
        return {
            "text": text,
            "evidence": evidence,
            "selected_category": selected_category,
            "category_match": category_match,
            "category_match_confidence": text.get("confidence") if category_match else None,
            "severity": text.get("suggested_priority", "medium"),
            "confidence": text.get("confidence"),
            "confidence_status": text.get("confidence_status", "unavailable"),
            "suspicious": False,
            "suspicious_reasons": [],
            "requires_human_review": True,
            "is_mock": False,
            "limitations": [
                "Evidence was not analyzed because the AI service was unavailable.",
                "AI output is advisory and cannot conclusively prove authenticity or manipulation.",
            ],
        }

    async def check_spam(
        self,
        text: str,
        user_submission_count: int = 0,
    ) -> dict[str, Any]:
        """Check complaint text for potential spam. Results are advisory."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.ai_url}/check-spam",
                    data={
                        "text": text,
                        "user_submission_count": user_submission_count,
                    },
                )
                response.raise_for_status()
                result = response.json()
                return {
                    "is_spam": bool(result.get("is_spam", False)),
                    "spam_score": float(result.get("spam_score", 0.0)),
                    "reasons": result.get("reasons", []),
                    "is_mock": bool(result.get("is_mock", False)),
                    "check_unavailable": False,
                }
        except Exception as exc:
            logger.warning(
                "ai_client.spam_check_unavailable",
                error=str(exc),
            )
            # Never reject a citizen's complaint because AI is unavailable.
            return {
                "is_spam": False,
                "spam_score": 0.0,
                "reasons": ["Spam assessment unavailable; manual review recommended."],
                "is_mock": False,
                "check_unavailable": True,
            }

    async def check_duplicates(
        self,
        title: str,
        description: str,
        category: str,
        latitude: float | None,
        longitude: float | None,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Calculate duplicate scores across potential nearby candidates."""
        results = []
        for cand in candidates:
            # Normalize punctuation so duplicate detection is stable across reports.
            cand_text = re.sub(r"[^a-z0-9\s]", " ", f"{cand.get('title', '')} {cand.get('description', '')}".lower())
            query_text = re.sub(r"[^a-z0-9\s]", " ", f"{title} {description}".lower())
            words1 = set(cand_text.split())
            words2 = set(query_text.split())
            jaccard = len(words1.intersection(words2)) / max(len(words1.union(words2)), 1)

            # Category boost
            cat_match = cand.get("category_slug") == category
            geo_score = 0.0
            if latitude is not None and longitude is not None and cand.get("latitude") is not None and cand.get("longitude") is not None:
                distance_km = _distance_km(latitude, longitude, cand["latitude"], cand["longitude"])
                geo_score = max(0.0, 1.0 - (distance_km / 2.0))
            score = (jaccard * 0.55) + (0.25 if cat_match else 0.0) + (geo_score * 0.20)

            if score > 0.4:
                results.append({
                    "id": cand.get("id"),
                    "public_id": cand.get("public_id"),
                    "title": cand.get("title"),
                    "status": cand.get("status"),
                    "category_name": cand.get("category_name"),
                    "similarity_score": round(score, 2),
                    "distance_meters": round(distance_km * 1000, 1) if geo_score else None,
                    "created_at": cand.get("created_at"),
                })
        return sorted(results, key=lambda x: x["similarity_score"], reverse=True)


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    lat_delta = radians(lat2 - lat1)
    lon_delta = radians(lon2 - lon1)
    value = sin(lat_delta / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(lon_delta / 2) ** 2
    return radius * 2 * asin(sqrt(value))


ai_client = AIClient()
