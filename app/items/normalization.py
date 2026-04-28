"""Normalize item payloads from eBay SDK responses for storage."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any


def normalize_item_payload(item_data: dict[str, Any]) -> dict[str, Any]:
    """Return a storage-ready item payload from parsed or raw SDK item data."""
    price = _money_value(item_data.get("price"))
    current_bid_source = item_data.get("current_bid", item_data.get("currentBidPrice"))
    current_bid = _money_value(current_bid_source)
    currency = _money_currency(item_data.get("price")) or item_data.get("currency")
    current_bid_currency = _money_currency(
        item_data.get("currentBidPrice")
    ) or item_data.get("current_bid_currency")
    location = _location(item_data)
    buying_options = item_data.get("buying_options", item_data.get("buyingOptions"))

    normalized = {
        "ebay_id": item_data.get("ebay_id") or item_data.get("itemId"),
        "legacy_id": item_data.get("legacy_id") or item_data.get("legacyItemId"),
        "title": item_data.get("title"),
        "price": price,
        "current_bid": current_bid,
        "current_bid_currency": current_bid_currency,
        "currency": currency,
        "url": item_data.get("url") or item_data.get("itemWebUrl"),
        "image_url": _image_url(item_data),
        "seller": _seller(item_data),
        "seller_rating": _seller_rating(item_data),
        "condition": item_data.get("condition"),
        "location": location,
        "location_country": location.get("country"),
        "postal_code": location.get("postal_code"),
        "start_time": _datetime_value(
            item_data.get("start_time") or item_data.get("itemCreationDate")
        ),
        "end_time": _datetime_value(
            item_data.get("end_time") or item_data.get("itemEndDate")
        ),
        "buying_options": _json_text(buying_options),
        "auction_details": _auction_details(item_data, buying_options),
        "categories": _categories(item_data),
        "marketplace": item_data.get("marketplace")
        or item_data.get("marketplace_id")
        or item_data.get("listingMarketplaceId"),
        "images": _images(item_data),
    }

    return {key: value for key, value in normalized.items() if value is not None}


def _money_value(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value")
    if value in (None, ""):
        return None
    return float(value)


def _money_currency(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("currency")
    return None


def _datetime_value(value: Any) -> datetime | None:
    if isinstance(value, datetime) or value is None:
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None


def _location(item_data: dict[str, Any]) -> dict[str, Any]:
    location = item_data.get("location") or item_data.get("itemLocation") or {}
    return {
        "country": location.get("country"),
        "postal_code": location.get("postal_code") or location.get("postalCode"),
    }


def _image_url(item_data: dict[str, Any]) -> str | None:
    image = item_data.get("image") or {}
    return item_data.get("image_url") or image.get("imageUrl")


def _seller(item_data: dict[str, Any]) -> str | None:
    seller = item_data.get("seller")
    if isinstance(seller, dict):
        return seller.get("username")
    return seller


def _seller_rating(item_data: dict[str, Any]) -> Any:
    seller = item_data.get("seller")
    if isinstance(seller, dict):
        return seller.get("feedbackPercentage")
    return item_data.get("seller_rating")


def _auction_details(item_data: dict[str, Any], buying_options: Any) -> str | None:
    if item_data.get("auction_details"):
        return _json_text(item_data["auction_details"])
    if "AUCTION" not in _buying_options_list(buying_options):
        return None

    current_bid_price = item_data.get("currentBidPrice", {})
    current_bid_currency = (
        _money_currency(current_bid_price) or item_data.get("currency") or "GBP"
    )
    auction_data = {
        "bid_count": item_data.get("bidCount", 0),
        "current_bid": {
            "value": _money_value(current_bid_price) or 0,
            "currency": current_bid_currency,
        },
        "end_time": item_data.get("itemEndDate"),
        "marketplace_id": item_data.get("listingMarketplaceId"),
    }
    return json.dumps(auction_data)


def _categories(item_data: dict[str, Any]) -> str | None:
    categories = item_data.get("categories")
    if not categories:
        return None
    if isinstance(categories, str):
        return categories
    return json.dumps(
        {
            "ids": [category["categoryId"] for category in categories],
            "names": [category["categoryName"] for category in categories],
        }
    )


def _images(item_data: dict[str, Any]) -> str | None:
    images = item_data.get("images")
    if images:
        return _json_text(images)

    image_url = _image_url(item_data)
    thumbnails = [
        image.get("imageUrl") for image in item_data.get("thumbnailImages", [])
    ]
    if not image_url and not thumbnails:
        return None
    return json.dumps({"main": image_url, "thumbnails": thumbnails})


def _json_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _buying_options_list(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return [option.strip() for option in value.split("|") if option.strip()]
        return decoded if isinstance(decoded, list) else []
    return value or []
