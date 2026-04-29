import json
from typing import Any

from ebay_client.time import parse_ebay_datetime

ItemSummary = dict[str, Any]
ParsedItem = dict[str, Any]
Money = dict[str, Any]


def parse_item_summary_response(
    response: dict[str, Any], default_currency: str = "GBP"
) -> list[ParsedItem]:
    """Parse an eBay Browse item summary response into application item dicts."""
    return [
        _map_item_summary(item_data, default_currency)
        for item_data in response.get("itemSummaries", [])
    ]


def _map_item_summary(item_data: ItemSummary, default_currency: str) -> ParsedItem:
    """Map one eBay item summary to the app's expected flattened item shape."""
    base_price = _parse_money(item_data.get("price"), default_currency)
    raw_buying_options = item_data.get("buyingOptions", [])
    auction_details = _parse_auction_details(
        item_data, raw_buying_options, default_currency
    )
    shipping = _shipping_details(item_data, default_currency)
    thumbnails = item_data.get("thumbnailImages") or []

    return {
        "ebay_id": item_data.get("itemId"),
        "legacy_id": item_data.get("legacyItemId"),
        "title": item_data.get("title", "No Title"),
        "short_description": item_data.get("shortDescription"),
        "price": base_price["value"],
        "current_bid": _current_bid_value(auction_details),
        "current_bid_currency": _current_bid_currency(
            auction_details, base_price, default_currency
        ),
        "currency": base_price["currency"],
        "url": item_data.get("itemWebUrl"),
        "image_url": _image_url(item_data),
        **_seller_details(item_data),
        "top_rated_seller": bool(item_data.get("topRatedBuyingExperience")),
        "shipping_cost": shipping["cost"],
        "free_shipping": shipping["free"],
        "condition": item_data.get("condition"),
        "location": _location(item_data),
        **_datetime_fields(item_data),
        "buying_options": json.dumps(raw_buying_options),
        "auction_details": json.dumps(auction_details) if auction_details else None,
        "categories": json.dumps(_categories(item_data)),
        "marketplace": item_data.get("listingMarketplaceId"),
        "images": json.dumps(_images(item_data)),
        "image_count": 1 + len(thumbnails) if _image_url(item_data) else len(thumbnails),
        "watch_count": item_data.get("watchCount"),
    }


def _parse_money(price_info: dict[str, Any] | None, default_currency: str) -> Money:
    """Parse eBay money fields while preserving the default currency fallback."""
    raw_price = price_info or {}

    return {
        "value": float(raw_price.get("value", 0)),
        "currency": raw_price.get("currency", default_currency),
    }


def _parse_auction_details(
    item_data: ItemSummary, buying_options: list[str], default_currency: str
) -> dict[str, Any] | None:
    """Build auction metadata for auction listings only."""
    if "AUCTION" not in buying_options:
        return None

    return {
        "bid_count": item_data.get("bidCount", 0),
        "current_bid": _parse_money(item_data.get("currentBidPrice"), default_currency),
        "end_time": item_data.get("itemEndDate"),
        "marketplace_id": item_data.get("listingMarketplaceId"),
    }


def _current_bid_value(auction_details: dict[str, Any] | None) -> float | int:
    """Return the numeric current bid used by the flattened item shape."""
    if auction_details and "current_bid" in auction_details:
        return auction_details["current_bid"]["value"]

    return 0


def _current_bid_currency(
    auction_details: dict[str, Any] | None, base_price: Money, default_currency: str
) -> Any:
    """Return the current bid currency, falling back to the listing currency."""
    if auction_details and "current_bid" in auction_details:
        return auction_details["current_bid"]["currency"]

    return base_price.get("currency", default_currency)


def _seller_details(item_data: ItemSummary) -> dict[str, Any]:
    """Extract seller identity and rating fields."""
    seller = item_data.get("seller", {})

    return {
        "seller": seller.get("username"),
        "seller_rating": seller.get("feedbackPercentage"),
    }


def _location(item_data: ItemSummary) -> dict[str, Any]:
    """Extract item location details."""
    item_location = item_data.get("itemLocation", {})

    return {
        "country": item_location.get("country"),
        "postal_code": item_location.get("postalCode"),
    }


def _datetime_fields(item_data: ItemSummary) -> dict[str, Any]:
    """Parse date fields into datetime objects."""
    return {
        "start_time": parse_ebay_datetime(item_data.get("itemCreationDate")),
        "end_time": parse_ebay_datetime(item_data.get("itemEndDate")),
    }


def _categories(item_data: ItemSummary) -> dict[str, list[str]]:
    """Extract category identifiers and names."""
    categories = item_data.get("categories", [])

    return {
        "ids": [category["categoryId"] for category in categories],
        "names": [category["categoryName"] for category in categories],
    }


def _image_url(item_data: ItemSummary) -> str | None:
    """Return the primary listing image URL."""
    return item_data.get("image", {}).get("imageUrl")


def _images(item_data: ItemSummary) -> dict[str, Any]:
    """Extract the main image and thumbnail image URLs."""
    return {
        "main": _image_url(item_data),
        "thumbnails": [
            image.get("imageUrl") for image in item_data.get("thumbnailImages", [])
        ],
    }


def _shipping_details(
    item_data: ItemSummary, default_currency: str
) -> dict[str, Any]:
    """Pull the cheapest shipping option (cost, free flag) from the response."""
    options = item_data.get("shippingOptions") or []
    if not options:
        return {"cost": None, "free": None}

    primary = options[0]
    cost_money = _parse_money(primary.get("shippingCost"), default_currency)
    cost = cost_money["value"]
    is_free = cost == 0 or primary.get("type") == "PICKUP"
    return {"cost": cost, "free": bool(is_free)}
