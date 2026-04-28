import time
from typing import Callable, Mapping, Optional

from ebay_client.browse.responses import dedupe_items

FetchPage = Callable[[int], Mapping[str, object]]
ParsePage = Callable[[Mapping[str, object]], list[dict[str, object]]]
Sleeper = Callable[[float], None]


def collect_unique_paginated_items(
    fetch_page: FetchPage,
    parse_page: ParsePage,
    *,
    max_pages: Optional[int],
    page_size: int,
    page_delay_seconds: float = 1,
    sleeper: Optional[Sleeper] = None,
) -> list[dict[str, object]]:
    """Collect paginated Browse items until max pages or a short page is reached."""
    returned_items: list[dict[str, object]] = []
    pages_searched = 0
    offset = 0
    sleep = sleeper or time.sleep

    while max_pages is None or pages_searched < max_pages:
        sleep(page_delay_seconds)
        raw_response = fetch_page(offset)
        parsed_items = parse_page(raw_response)
        returned_items.extend(parsed_items)

        pages_searched += 1
        offset += len(parsed_items)
        if len(parsed_items) < page_size:
            break

    return dedupe_items(returned_items)
