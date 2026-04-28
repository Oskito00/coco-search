from datetime import datetime, timezone
from typing import TypeGuard


def parse_ebay_datetime(value: str | None) -> datetime | None:
    """Parse an eBay datetime value into a timezone-aware datetime."""
    if not _is_datetime_value(value):
        return None

    return _parse_utc_datetime(value) or _parse_iso_datetime(value)


def _is_datetime_value(value: str | None) -> TypeGuard[str]:
    """Return whether a value is a non-empty datetime string."""
    return isinstance(value, str) and bool(value)


def _parse_utc_datetime(value: str) -> datetime | None:
    """Parse eBay's millisecond UTC timestamp format."""
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def _parse_iso_datetime(value: str) -> datetime | None:
    """Parse ISO datetimes, including values that end with Z."""
    try:
        return datetime.fromisoformat(_normalise_utc_suffix(value))
    except ValueError:
        return None


def _normalise_utc_suffix(value: str) -> str:
    """Return a datetime string that datetime.fromisoformat accepts."""
    if value.endswith("Z"):
        return f"{value[:-1]}+00:00"
    return value
