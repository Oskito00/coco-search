"""Search request construction helpers for eBay Browse API."""

from collections.abc import Mapping
from typing import Any

from ebay_client.browse.dto import SearchFilters, SearchRequest


def create_search_request(
    *,
    keywords: str,
    filters: Mapping[str, Any] | SearchFilters | None,
    limit: int,
    offset: int,
    sort_order: str | None,
) -> SearchRequest:
    """Create a normalized search request DTO from public method arguments."""
    search_filters = (
        filters
        if isinstance(filters, SearchFilters)
        else SearchFilters.from_mapping(filters)
    )
    return SearchRequest(
        keywords=keywords,
        filters=search_filters,
        limit=limit,
        offset=offset,
        sort_order=sort_order,
    )


def build_search_params(
    request: SearchRequest,
    filter_value: str | None,
) -> dict[str, str | int]:
    """Build query params for the item summary search endpoint."""
    params: dict[str, str | int] = {
        "q": request.keywords,
        "limit": request.limit,
        "offset": request.offset,
    }

    if request.sort_order:
        params["sort"] = request.sort_order

    if filter_value:
        params["filter"] = filter_value

    return params
