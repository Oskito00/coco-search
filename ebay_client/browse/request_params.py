from typing import Mapping, Optional

from ebay_client.browse.dto import SearchFilters, SearchRequest


def create_search_request(
    keywords: str,
    filters: Optional[Mapping[str, object]],
    limit: int,
    offset: int,
    sort_order: Optional[str],
) -> SearchRequest:
    """Create a normalized search request from public client arguments."""
    return SearchRequest(
        keywords=keywords,
        filters=SearchFilters.from_mapping(filters),
        limit=limit,
        offset=offset,
        sort_order=sort_order,
    )


def build_search_params(
    request: SearchRequest,
    filter_value: Optional[str],
) -> dict[str, object]:
    """Build query parameters for an item summary search request."""
    params: dict[str, object] = {
        "q": request.keywords,
        "limit": request.limit,
        "offset": request.offset,
    }

    if request.sort_order:
        params["sort"] = request.sort_order

    if filter_value:
        params["filter"] = filter_value

    return params
