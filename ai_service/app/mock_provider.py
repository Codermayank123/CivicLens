"""Deterministic mock AI for development and automated tests."""

from __future__ import annotations

from app.constants import URGENCY_KEYWORDS
from app.schemas import (
    DuplicateDetectionResult,
    ImageClassificationResult,
    SpamCheckResult,
    TextClassificationResult,
)


class MockAIProvider:
    def classify_image(self, filename: str | None = None) -> ImageClassificationResult:
        return ImageClassificationResult(
            category="other",
            confidence=0.0,
            is_mock=True,
            is_relevant=False,
            message="Test mode: image contents are not analyzed.",
            top_predictions=[{"category": "other", "confidence": 0.0}],
        )

    def classify_text(self, text: str) -> TextClassificationResult:
        text_lower = text.lower()
        category = "other"
        confidence = 0.4

        keyword_map = {
            "pothole": ["pothole", "hole in road", "pit", "crater"],
            "garbage": ["garbage", "trash", "waste", "dump", "litter", "rubbish"],
            "broken_streetlight": ["streetlight", "lamp", "light pole", "dark street"],
            "water_leakage": ["water leak", "pipe burst", "water flowing", "leaking"],
            "damaged_road": ["road damage", "broken road", "crack in road", "road condition"],
            "drainage_problem": ["drain", "sewer", "clog", "flooding", "waterlog"],
            "public_safety": ["dangerous", "unsafe", "hazard", "risk", "exposed wire"],
            "traffic_signal": ["traffic light", "signal", "traffic sign", "crossing"],
        }

        for cat, keywords in keyword_map.items():
            for kw in keywords:
                if kw in text_lower:
                    category = cat
                    confidence = 0.82
                    break
            if category != "other":
                break

        urgency = "medium"
        for level, keywords in URGENCY_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    urgency = level
                    break

        priority_map = {"high": "high", "medium": "medium", "low": "low"}
        found_keywords = [w for w in text_lower.split() if len(w) > 3 and w.isalpha()][:10]

        return TextClassificationResult(
            category=category,
            confidence=confidence,
            keywords=found_keywords,
            urgency=urgency,
            suggested_priority=priority_map.get(urgency, "medium"),
            is_mock=True,
            is_relevant=category != "other",
            message=(
                None
                if category != "other"
                else "Test mode could not identify a civic issue; please review the description."
            ),
        )

    def check_spam(self, text: str, user_submission_count: int = 0) -> SpamCheckResult:
        reasons: list[str] = []
        score = 0.0
        if len(text) < 10:
            score += 0.3
            reasons.append("Very short description")
        if user_submission_count > 10:
            score += 0.4
            reasons.append("High submission frequency")
        return SpamCheckResult(
            is_spam=score > 0.6,
            spam_score=min(score, 1.0),
            reasons=reasons,
            is_mock=True,
        )

    def find_duplicates(self, text: str, category: str, latitude: float, longitude: float) -> DuplicateDetectionResult:
        return DuplicateDetectionResult(duplicates=[], is_mock=True)


mock_provider = MockAIProvider()
