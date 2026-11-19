"""
OpenAI-compatible chat/vision API provider for civic complaint analysis.

Works with OpenAI, Azure OpenAI, and other vendors that expose the same REST shape.
"""

from __future__ import annotations

import asyncio
import base64
import json
import re
from typing import Any

import httpx
import structlog

from app.constants import CATEGORY_DEPARTMENTS, CATEGORIES, URGENCY_KEYWORDS
from app.schemas import (
    ComplaintVerificationResult,
    DuplicateDetectionResult,
    ImageClassificationResult,
    SpamCheckResult,
    TextClassificationResult,
)

logger = structlog.get_logger()

_TEXT_SYSTEM = """You classify Indian municipal / civic complaints for routing to the correct department.
Respond with a single JSON object only (no markdown), using this schema:
{
  "category": "<one of: """
_TEXT_SYSTEM += ", ".join(CATEGORIES)
_TEXT_SYSTEM += """>",
  "confidence": <float 0.0-1.0>,
  "department": <responsible department name when identifiable>,
  "urgency": "low"|"medium"|"high",
  "suggested_priority": "low"|"medium"|"high"|"critical",
  "is_relevant": <true if the text describes a real civic/municipal issue>,
  "message": <optional short note for citizens when is_relevant is false>,
  "keywords": [<up to 8 significant words from the text>]
}
Use category \"other\" with low confidence when the text is unrelated to civic infrastructure or public services."""


_IMAGE_SYSTEM = """You classify photos submitted as civic complaint evidence.
Respond with JSON only:
{
  "category": "<one of: """
_IMAGE_SYSTEM += ", ".join(CATEGORIES)
_IMAGE_SYSTEM += """>",
  "confidence": <float 0.0-1.0>,
  "is_relevant": <true if the image shows a civic/municipal problem>,
  "message": <optional note when not relevant>,
  "top_predictions": [{"category": "...", "confidence": 0.0-1.0}, ... up to 3]
}
If the image is unrelated (selfies, memes, documents, blank), set category to other, confidence below 0.3, is_relevant false.
You may identify authenticity or manipulation indicators such as visible editing artifacts, repeated
patterns, inconsistent lighting, screenshots, or missing context, but you cannot prove an image is
genuine or manipulated. Always state uncertainty through requires_human_review when appropriate.
Also return:
  "evidence_quality": "clear"|"partial"|"poor"|"unknown",
  "authenticity_indicators": ["..."],
  "manipulation_indicators": ["..."],
  "suspicious": <true only when indicators warrant human review>,
  "requires_human_review": <true when evidence is uncertain or suspicious>"""


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        text_model: str,
        vision_model: str,
        timeout_seconds: float,
        review_confidence_threshold: float,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._text_model = text_model
        self._vision_model = vision_model
        self._timeout = timeout_seconds
        self._review_threshold = review_confidence_threshold

    async def _chat_json(
        self,
        model: str,
        system: str,
        user_content: str | list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
        }
        # Gemini's OpenAI-compatibility layer currently does not reliably
        # support OpenAI's response_format extension. The prompts already
        # require JSON and the parser below validates the returned object.
        if "generativelanguage.googleapis.com" not in self._base_url:
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        # Temporary provider demand (common on Gemini) often returns HTTP 503.
        # Retry a small number of times before failing closed to human review.
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(3):
                try:
                    res = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                except httpx.TimeoutException as exc:
                    last_error = exc
                    logger.warning(
                        "ai.openai_compatible.timeout",
                        attempt=attempt + 1,
                        model=model,
                    )
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue

                if res.status_code == 503:
                    last_error = httpx.HTTPStatusError(
                        "AI provider unavailable",
                        request=res.request,
                        response=res,
                    )
                    logger.warning(
                        "ai.openai_compatible.provider_busy",
                        attempt=attempt + 1,
                        status=503,
                        body=res.text[:300],
                    )
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue

                if res.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        "AI provider unavailable",
                        request=res.request,
                        response=res,
                    )
                if res.status_code >= 400:
                    logger.warning(
                        "ai.openai_compatible.client_error",
                        status=res.status_code,
                        body=res.text[:500],
                    )
                    raise httpx.HTTPStatusError(
                        "AI provider rejected request",
                        request=res.request,
                        response=res,
                    )
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                return _parse_json_object(content)

        if last_error is not None:
            raise last_error
        raise RuntimeError("AI provider request failed without a response")

    async def classify_text(self, text: str) -> TextClassificationResult:
        parsed = await self._chat_json(
            self._text_model,
            _TEXT_SYSTEM,
            text[:8000],
        )
        category = _normalize_category(parsed.get("category"))
        confidence = _optional_confidence(parsed.get("confidence"))
        urgency = _normalize_urgency(parsed.get("urgency"))
        # Relevance is about whether the text describes a civic issue.
        # Low or missing confidence means human review — not "not a civic issue".
        if "is_relevant" in parsed:
            is_relevant = bool(parsed.get("is_relevant")) and category != "other"
        else:
            is_relevant = category != "other"
        return TextClassificationResult(
            category=category,
            confidence=confidence,
            confidence_status="available" if confidence is not None else "unavailable",
            department=CATEGORY_DEPARTMENTS.get(category) or parsed.get("department"),
            keywords=_as_str_list(parsed.get("keywords")),
            urgency=urgency,
            suggested_priority=_normalize_priority(parsed.get("suggested_priority"), urgency),
            is_mock=False,
            is_relevant=is_relevant,
            message=parsed.get("message"),
        )

    async def classify_image(
        self,
        *,
        filename: str | None,
        content: bytes,
        mime_type: str,
    ) -> ImageClassificationResult:
        if not content:
            return ImageClassificationResult(
                category="other",
                confidence=0.0,
                confidence_status="available",
                is_mock=False,
                is_relevant=False,
                message="Empty image upload.",
                top_predictions=[{"category": "other", "confidence": 0.0}],
            )
        b64 = base64.standard_b64encode(content).decode("ascii")
        data_url = f"data:{mime_type};base64,{b64}"
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": f"Filename: {filename or 'unknown'}. Classify this civic complaint photo.",
            },
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
        parsed = await self._chat_json(self._vision_model, _IMAGE_SYSTEM, user_content)
        category = _normalize_category(parsed.get("category"))
        confidence = _optional_confidence(parsed.get("confidence"))
        is_relevant = bool(parsed.get("is_relevant", category != "other" and confidence is not None))
        if category == "other" or confidence is None or confidence < self._review_threshold:
            is_relevant = False
        top = parsed.get("top_predictions")
        if not isinstance(top, list):
            top = [{"category": category, "confidence": confidence}] if confidence is not None else []
        return ImageClassificationResult(
            category=category,
            confidence=confidence,
            confidence_status="available" if confidence is not None else "unavailable",
            department=CATEGORY_DEPARTMENTS.get(category),
            is_mock=False,
            is_relevant=is_relevant,
            message=parsed.get("message"),
            top_predictions=top[:3],
            evidence_quality=_normalize_evidence_quality(parsed.get("evidence_quality")),
            authenticity_indicators=_as_str_list(parsed.get("authenticity_indicators")),
            manipulation_indicators=_as_str_list(parsed.get("manipulation_indicators")),
            suspicious=bool(parsed.get("suspicious", False)),
            requires_human_review=bool(
                parsed.get("requires_human_review", not is_relevant or confidence is None or confidence < self._review_threshold)
            ) or not is_relevant or confidence is None or confidence < self._review_threshold,
            media_type="image",
        )

    async def verify_complaint(
        self,
        *,
        title: str,
        description: str,
        selected_category: str,
        evidence: list[tuple[str | None, bytes, str]],
    ) -> ComplaintVerificationResult:
        text = await self.classify_text(
            f"Selected category: {selected_category}.\nTitle: {title}\nDescription: {description}"
        )
        evidence_results: list[ImageClassificationResult] = []
        for filename, content, mime_type in evidence:
            if mime_type.startswith("image/"):
                evidence_results.append(
                    await self.classify_image(
                        filename=filename, content=content, mime_type=mime_type
                    )
                )
            else:
                # The chat vision contract accepts images, not arbitrary video bytes. The
                # backend may provide extracted frames; otherwise this remains explicitly
                # uncertain and is routed to a person.
                evidence_results.append(
                    ImageClassificationResult(
                        category="other",
                        confidence=0.0,
                        is_mock=False,
                        is_relevant=False,
                        message="Video frame analysis is unavailable in this AI deployment; human review is required.",
                        evidence_quality="unknown",
                        suspicious=False,
                        requires_human_review=True,
                        media_type="video",
                    )
                )

        matching_scores = [
            item.confidence
            for item in [text, *evidence_results]
            if item.category == selected_category and item.is_relevant and item.confidence is not None
        ]
        category_match_confidence = max(matching_scores, default=None)
        category_match = text.category == selected_category and text.is_relevant
        suspicious_reasons = [
            reason
            for result in evidence_results
            for reason in result.manipulation_indicators
        ]
        suspicious = bool(suspicious_reasons) or any(result.suspicious for result in evidence_results)
        requires_human_review = (
            not category_match
            or text.confidence is None
            or text.confidence < self._review_threshold
            or any(result.requires_human_review for result in evidence_results)
            or suspicious
        )
        all_confidences = [text.confidence, *(result.confidence for result in evidence_results)]
        confidence = min(all_confidences) if all(value is not None for value in all_confidences) else None
        limitations = [
            "AI output is advisory and cannot conclusively prove authenticity, intent, or manipulation.",
            "Uncertain or suspicious evidence must be reviewed by an authorized officer.",
        ]
        return ComplaintVerificationResult(
            text=text,
            evidence=evidence_results,
            selected_category=selected_category,
            category_match=category_match,
            category_match_confidence=category_match_confidence,
            severity=text.suggested_priority,
            confidence=confidence,
            confidence_status="available" if confidence is not None else "unavailable",
            suspicious=suspicious,
            suspicious_reasons=suspicious_reasons,
            requires_human_review=requires_human_review,
            is_mock=text.is_mock or any(result.is_mock for result in evidence_results),
            limitations=limitations,
        )

    async def check_spam(self, text: str, user_submission_count: int = 0) -> SpamCheckResult:
        prompt = (
            f"Submission count in last 24h (approx): {user_submission_count}. "
            f"Text:\n{text[:4000]}\n\n"
            'Return JSON: {{"is_spam": bool, "spam_score": 0.0-1.0, "reasons": ["..."]}}'
        )
        parsed = await self._chat_json(
            self._text_model,
            "Detect spam or abusive civic complaint submissions. JSON only.",
            prompt,
        )
        score = _clamp_float(parsed.get("spam_score"), default=0.0)
        reasons = _as_str_list(parsed.get("reasons"))
        is_spam = bool(parsed.get("is_spam", score > 0.65))
        return SpamCheckResult(is_spam=is_spam, spam_score=score, reasons=reasons, is_mock=False)

    async def find_duplicates(
        self,
        text: str,
        category: str,
        latitude: float,
        longitude: float,
    ) -> DuplicateDetectionResult:
        return DuplicateDetectionResult(duplicates=[], is_mock=False)


def _parse_json_object(content: str) -> dict[str, Any]:
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _normalize_category(value: Any) -> str:
    if not isinstance(value, str):
        return "other"
    slug = value.strip().lower().replace(" ", "_")
    return slug if slug in CATEGORIES else "other"


def _normalize_urgency(value: Any) -> str:
    if isinstance(value, str) and value.lower() in URGENCY_KEYWORDS:
        return value.lower()
    return "medium"


def _normalize_priority(value: Any, urgency: str) -> str:
    allowed = {"low", "medium", "high", "critical"}
    if isinstance(value, str) and value.lower() in allowed:
        return value.lower()
    if urgency == "high":
        return "high"
    return "medium"


def _clamp_float(value: Any, default: float) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, num))


def _optional_confidence(value: Any) -> float | None:
    """Return a provider score only when the provider actually supplied one."""
    if value is None or isinstance(value, bool):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, num))


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None][:10]


def _normalize_evidence_quality(value: Any) -> str:
    if isinstance(value, str) and value.lower() in {"clear", "partial", "poor", "unknown"}:
        return value.lower()
    return "unknown"
