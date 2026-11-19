"""Small MongoDB helpers shared by services.

The application uses string UUIDs as public identifiers and deliberately does not
expose Mongo's internal ``_id`` field. Keeping conversion in one place prevents
accidental serialization of driver-specific values in API responses.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def model_to_doc(model: BaseModel) -> dict[str, Any]:
    """Convert a Pydantic model to a Mongo document with stable string IDs."""
    data = model.model_dump(mode="python")
    data["_id"] = data.pop("id")
    return _normalise_enums(data)


def _normalise_enums(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {key: _normalise_enums(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalise_enums(item) for item in value]
    return value


def doc_to_model(model_type: type[ModelT], document: dict[str, Any] | None) -> ModelT | None:
    """Validate a Mongo document as a Pydantic domain model."""
    if document is None:
        return None
    payload = dict(document)
    payload["id"] = str(payload.pop("_id", payload.get("id")))
    return model_type.model_validate(payload)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """Normalize MongoDB's naive UTC datetimes before application comparisons."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
