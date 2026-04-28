"""Datetime parsing and serialization helpers for token metadata."""

from __future__ import annotations

from datetime import datetime, timezone


def parse_datetime(value: object) -> datetime | None:
    """Return an aware UTC datetime from common token-store values."""
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        normalized = value
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"Invalid datetime value: {value!r}") from exc
    else:
        raise TypeError(f"Unsupported datetime value: {value!r}")

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def serialize_datetime(value: object) -> str | None:
    """Return an ISO-8601 string for a datetime-like value."""
    parsed = parse_datetime(value)
    if parsed is None:
        return None
    return parsed.isoformat()
