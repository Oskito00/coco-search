"""JSON-safe serialization for domain event and observation payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def serialize_for_persistence(value: Any) -> Any:
    """Return a JSON-safe deep copy of *value* (datetimes -> ISO 8601)."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: serialize_for_persistence(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_for_persistence(item) for item in value]
    return value
