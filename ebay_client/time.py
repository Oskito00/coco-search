"""Date and time utilities for eBay payloads."""

from datetime import datetime, timezone

EBAY_UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def parse_ebay_datetime(value: str | None) -> datetime | None:
    """Parse supported eBay datetime values.

    Returns ``None`` for missing or invalid input.
    """
    if not value:
        return None

    return _parse_utc_datetime(value) or _parse_iso_datetime(value)


def _parse_utc_datetime(value: str) -> datetime | None:
    """Parse eBay's canonical UTC datetime format."""
    try:
        return datetime.strptime(value, EBAY_UTC_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_iso_datetime(value: str) -> datetime | None:
    """Parse ISO datetimes, including values with a trailing ``Z``."""
    try:
        return datetime.fromisoformat(_normalize_z_suffix(value))
    except ValueError:
        return None


def _normalize_z_suffix(value: str) -> str:
    """Convert an ISO trailing ``Z`` timezone marker to ``+00:00``."""
    if value.endswith("Z"):
        return f"{value[:-1]}+00:00"
    return value
