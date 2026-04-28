"""Pagination helpers for eBay Browse search results."""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ebay_client.browse.responses import dedupe_items

ParsedItem = dict[str, Any]
RawResponse = Mapping[str, Any]


def collect_search_items(
    *,
    fetch_page: Callable[[int, int], RawResponse],
    parse_page: Callable[[RawResponse], Sequence[ParsedItem]],
    max_pages: int | None,
    sleeper: Callable[[float], None],
    page_delay_seconds: float = 1.0,
    page_size: int = 200,
) -> list[ParsedItem]:
    """Fetch, parse, and dedupe paginated Browse search results."""
    returned_items: list[ParsedItem] = []
    pages_searched = 0
    offset = 0

    while max_pages is None or pages_searched < max_pages:
        sleeper(page_delay_seconds)
        parsed_items = list(parse_page(fetch_page(offset, page_size)))
        returned_items.extend(parsed_items)

        offset += len(parsed_items)
        pages_searched += 1
        if len(parsed_items) < page_size:
            break

    return dedupe_items(returned_items)
