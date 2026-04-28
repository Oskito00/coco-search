"""Item summary mapping for eBay Browse responses."""

import json
from typing import Any, Mapping

from ebay_client.browse.auction import (
    build_auction_details,
    get_current_bid_currency,
    get_current_bid_value,
    serialize_auction_details,
)
from ebay_client.browse.categories import serialize_categories
from ebay_client.browse.dates import parse_ebay_datetime
from ebay_client.browse.images import get_main_image_url, serialize_images
from ebay_client.browse.money import parse_money


def map_item_summary(
    item_data: Mapping[str, Any],
    default_currency: str,
) -> dict[str, Any]:
    """Map one eBay Browse item summary into the application's item shape."""
    base_price = parse_money(item_data.get("price"), default_currency)
    buying_options = _get_buying_options(item_data)
    auction_details = build_auction_details(
        item_data,
        buying_options,
        str(base_price["currency"]),
    )

    return {
        "ebay_id": item_data.get("itemId"),
        "legacy_id": item_data.get("legacyItemId"),
        "title": item_data.get("title", "No Title"),
        "price": base_price["value"],
        "current_bid": get_current_bid_value(auction_details),
        "current_bid_currency": get_current_bid_currency(auction_details, base_price),
        "currency": base_price["currency"],
        "url": item_data.get("itemWebUrl"),
        "image_url": get_main_image_url(item_data),
        "seller": _get_seller_value(item_data, "username"),
        "seller_rating": _get_seller_value(item_data, "feedbackPercentage"),
        "condition": item_data.get("condition"),
        "location": _get_location(item_data),
        "start_time": parse_ebay_datetime(item_data.get("itemCreationDate")),
        "end_time": parse_ebay_datetime(item_data.get("itemEndDate")),
        "buying_options": json.dumps(buying_options),
        "auction_details": serialize_auction_details(auction_details),
        "categories": serialize_categories(item_data.get("categories")),
        "marketplace": item_data.get("listingMarketplaceId"),
        "images": serialize_images(item_data),
    }


def _get_buying_options(item_data: Mapping[str, Any]) -> list[str]:
    buying_options = item_data.get("buyingOptions") or []
    return [str(option) for option in buying_options]


def _get_seller_value(item_data: Mapping[str, Any], field_name: str) -> Any:
    seller = item_data.get("seller") or {}
    if not isinstance(seller, Mapping):
        return None

    return seller.get(field_name)


def _get_location(item_data: Mapping[str, Any]) -> dict[str, Any]:
    location = item_data.get("itemLocation") or {}
    if not isinstance(location, Mapping):
        location = {}

    return {
        "country": location.get("country"),
        "postal_code": location.get("postalCode"),
    }
