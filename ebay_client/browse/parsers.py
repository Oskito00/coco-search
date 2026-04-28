"""Public parsers for eBay Browse API responses."""

from typing import Any, Mapping

from ebay_client.browse.item_mapping import map_item_summary


def parse_item_summary_response(
    response: Mapping[str, Any] | None,
    default_currency: str = "GBP",
) -> list[dict[str, Any]]:
    """Parse an eBay Browse item summary search response."""
    if not response:
        return []

    item_summaries = response.get("itemSummaries") or []
    return [
        map_item_summary(item_summary, default_currency)
        for item_summary in item_summaries
        if isinstance(item_summary, Mapping)
    ]
