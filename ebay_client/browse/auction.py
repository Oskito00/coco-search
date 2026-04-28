"""Auction parsing helpers for eBay Browse responses."""

import json
from typing import Any, Mapping, Sequence

from ebay_client.browse.money import Money, parse_money


def is_auction_item(buying_options: Sequence[str]) -> bool:
    """Return whether an item summary is listed as an auction."""
    return "AUCTION" in buying_options


def build_auction_details(
    item_data: Mapping[str, Any],
    buying_options: Sequence[str],
    default_currency: str,
) -> dict[str, Any] | None:
    """Build serialized auction payload data for auction item summaries."""
    if not is_auction_item(buying_options):
        return None

    current_bid = parse_money(item_data.get("currentBidPrice"), default_currency)

    return {
        "bid_count": item_data.get("bidCount", 0),
        "current_bid": current_bid,
        "end_time": item_data.get("itemEndDate"),
        "marketplace_id": item_data.get("listingMarketplaceId"),
    }


def serialize_auction_details(auction_details: Mapping[str, Any] | None) -> str | None:
    """Serialize auction details when an item summary has auction data."""
    if not auction_details:
        return None

    return json.dumps(auction_details)


def get_current_bid_value(auction_details: Mapping[str, Any] | None) -> float:
    """Return the current bid value for mapped item dictionaries."""
    current_bid = _get_current_bid(auction_details)
    return float(current_bid.get("value", 0.0)) if current_bid else 0.0


def get_current_bid_currency(
    auction_details: Mapping[str, Any] | None,
    base_price: Money,
) -> str:
    """Return the current bid currency, falling back to the base price currency."""
    current_bid = _get_current_bid(auction_details)
    if not current_bid:
        return str(base_price.get("currency", "GBP"))

    return str(current_bid.get("currency") or base_price.get("currency", "GBP"))


def _get_current_bid(
    auction_details: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    if not auction_details:
        return None

    current_bid = auction_details.get("current_bid")
    return current_bid if isinstance(current_bid, Mapping) else None
