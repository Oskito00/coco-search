"""Datetime parsing helpers for eBay Browse responses."""

from datetime import datetime, timezone


def parse_ebay_datetime(date_value: str | None) -> datetime | None:
    """Parse eBay Browse datetime strings into timezone-aware datetimes."""
    if not date_value:
        return None

    try:
        return datetime.strptime(date_value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        try:
            return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        except ValueError:
            return None
