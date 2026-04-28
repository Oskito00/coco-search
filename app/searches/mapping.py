from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from app.searches.definitions import SavedSearch, SearchFilters, SearchSchedule


def saved_search_from_model(user_query: Any) -> SavedSearch:
    """Map a UserQuery ORM object to a SavedSearch domain object."""

    keywords = _keywords_for_query(user_query)
    saved_search = SavedSearch(
        id=str(user_query.query_id),
        user_id=int(user_query.user_id),
        keyword_id=int(user_query.keyword_id),
        keywords=keywords,
        marketplace=user_query.marketplace or "EBAY_GB",
        is_active=bool(user_query.is_active),
        filters=SearchFilters(
            min_price=_optional_decimal(user_query.min_price),
            max_price=_optional_decimal(user_query.max_price),
            item_location=user_query.item_location,
            condition=user_query.condition,
            buying_options=user_query.buying_options or "FIXED_PRICE|AUCTION",
            required_keywords=user_query.required_keywords,
            excluded_keywords=user_query.excluded_keywords,
        ),
        schedule=SearchSchedule(
            check_interval=int(user_query.check_interval or 5),
            first_run=bool(user_query.first_run),
            last_full_run=user_query.last_full_run,
            next_full_run=user_query.next_full_run,
            last_recent_run=user_query.last_recent_run,
        ),
    )
    return saved_search


def to_ebay_search_params(saved_search: SavedSearch) -> dict[str, Any]:
    """Return public EbayClient search parameters for a saved search."""

    return {
        "keywords": saved_search.keywords,
        "filters": {
            "min_price": _decimal_to_float(saved_search.filters.min_price),
            "max_price": _decimal_to_float(saved_search.filters.max_price),
            "item_location": saved_search.filters.item_location,
            "condition": saved_search.filters.condition,
            "buying_options": saved_search.filters.buying_options,
        },
        "marketplace": saved_search.marketplace,
    }


def _keywords_for_query(user_query: Any) -> str:
    keyword = getattr(user_query, "keyword", None)
    if keyword is not None and getattr(keyword, "keyword_text", None):
        return str(keyword.keyword_text)
    if getattr(user_query, "keywords", None):
        return str(user_query.keywords)
    raise ValueError("Saved search requires keyword text")


def _optional_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    return Decimal(str(value))


def _decimal_to_float(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    return float(value)
