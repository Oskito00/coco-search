"""Raw, item-only feature extraction (no saved-search context).

The output is a flat dict of plain Python values that's safe to dump into a
JSONB column on :class:`ItemFeatureSnapshot`. Future scorers can compose
match-features (saved-search vs item) from these raw values without needing
to re-implement the parsing logic.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Optional

EMOJI_PATTERN = re.compile(
    "["
    "\U0001f300-\U0001f9ff"
    "\U00002600-\U000027bf"
    "\U0001fa70-\U0001faff"
    "]"
)

RAW_ITEM_FEATURE_KEYS: tuple[str, ...] = (
    "price",
    "currency",
    "condition",
    "buying_options",
    "has_auction",
    "has_fixed_price",
    "seller_feedback_pct",
    "top_rated_seller",
    "shipping_cost",
    "free_shipping",
    "location_country",
    "end_time",
    "current_bid",
    "title",
    "title_length",
    "title_word_count",
    "title_has_emoji",
    "short_description",
    "short_description_length",
    "categories",
    "image_count",
    "watch_count",
    "listing_age_seconds",
    "marketplace",
)


def extract_raw_item_features(
    item: Any, *, now: Optional[datetime] = None
) -> dict[str, Any]:
    """Return a flat dict of raw item features."""
    now = now or datetime.now(timezone.utc)
    title = _str(_attr(item, "title")) or ""
    short_description = _str(_attr(item, "short_description")) or ""
    buying_options_raw = _attr(item, "buying_options")
    buying_options_list = _buying_options_list(buying_options_raw)

    return {
        "price": _float_or_none(_attr(item, "price")),
        "currency": _attr(item, "currency"),
        "condition": _attr(item, "condition"),
        "buying_options": buying_options_list,
        "has_auction": "AUCTION" in buying_options_list,
        "has_fixed_price": "FIXED_PRICE" in buying_options_list,
        "seller_feedback_pct": _float_or_none(_attr(item, "seller_rating")),
        "top_rated_seller": _bool_or_none(_attr(item, "top_rated_seller")),
        "shipping_cost": _float_or_none(_attr(item, "shipping_cost")),
        "free_shipping": _bool_or_none(_attr(item, "free_shipping")),
        "location_country": _attr(item, "location_country"),
        "end_time": _isoformat(_attr(item, "end_time")),
        "current_bid": _float_or_none(_attr(item, "current_bid")),
        "title": title,
        "title_length": len(title),
        "title_word_count": len(title.split()) if title else 0,
        "title_has_emoji": bool(EMOJI_PATTERN.search(title)),
        "short_description": short_description,
        "short_description_length": len(short_description),
        "categories": _categories(_attr(item, "categories")),
        "image_count": _int_or_none(_attr(item, "image_count")),
        "watch_count": _int_or_none(_attr(item, "watch_count")),
        "listing_age_seconds": _listing_age_seconds(_attr(item, "start_time"), now),
        "marketplace": _attr(item, "marketplace"),
    }


def _attr(source: Any, name: str) -> Any:
    if source is None:
        return None
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _float_or_none(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> Optional[bool]:
    if value is None:
        return None
    return bool(value)


def _isoformat(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    if value in (None, ""):
        return None
    return str(value)


def _buying_options_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return [option.strip() for option in value.split("|") if option.strip()]
        if isinstance(decoded, list):
            return [str(v) for v in decoded]
    return []


def _categories(value: Any) -> dict[str, list[str]]:
    if value is None:
        return {"ids": [], "names": []}
    if isinstance(value, dict):
        return {
            "ids": list(value.get("ids") or []),
            "names": list(value.get("names") or []),
        }
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {"ids": [], "names": []}
        if isinstance(decoded, dict):
            return {
                "ids": list(decoded.get("ids") or []),
                "names": list(decoded.get("names") or []),
            }
    return {"ids": [], "names": []}


def _listing_age_seconds(start_time: Any, now: datetime) -> Optional[int]:
    if start_time is None:
        return None
    if isinstance(start_time, datetime):
        ref = start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)
        return int((now - ref).total_seconds())
    return None
