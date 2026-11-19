"""MongoDB AI prediction document used for traceability and review."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class AIPrediction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    complaint_id: str
    prediction_type: str
    predicted_category: str | None = None
    confidence: float | None = None
    is_mock: bool = False
    corrected_category: str | None = None
    was_correct: bool | None = None
    raw_output: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
