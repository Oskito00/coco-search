"""Pure helpers that compare an existing item against an incoming payload."""

from __future__ import annotations

from typing import Any, Optional

ITEM_DIFF_FIELDS = (
    "title",
    "price",
    "current_bid",
    "current_bid_currency",
    "currency",
    "url",
    "image_url",
    "seller",
    "seller_rating",
    "condition",
    "location_country",
    "postal_code",
    "start_time",
    "end_time",
    "buying_options",
    "auction_details",
    "categories",
    "marketplace",
    "images",
)


def diff_item(item: Any, item_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return ``{field: {"old": ..., "new": ...}}`` for every field that changed."""
    changes: dict[str, dict[str, Any]] = {}
    for field in ITEM_DIFF_FIELDS:
        if field not in item_data or not hasattr(item, field):
            continue
        old_value = getattr(item, field)
        new_value = item_data[field]
        if old_value != new_value:
            changes[field] = {"old": old_value, "new": new_value}
    return changes


def detect_price_drop(
    old_price: Any, new_price: Any
) -> Optional[tuple[float, float]]:
    """Return ``(old, new)`` floats when the price strictly dropped, else None."""
    if old_price is None or new_price is None or new_price >= old_price:
        return None
    return float(old_price), float(new_price)
