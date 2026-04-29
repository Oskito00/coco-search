"""Pure auction-window check used to gate auction-ending notifications."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

AUCTION_ALERT_WINDOW = timedelta(hours=12)


def is_ending_within(
    end_time: Optional[datetime],
    now: datetime,
    window: timedelta = AUCTION_ALERT_WINDOW,
) -> bool:
    """Return True iff *end_time* lies inside ``[now, now + window)``."""
    if end_time is None:
        return False
    end_time = _ensure_utc(end_time)
    return (end_time - now) < window


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
