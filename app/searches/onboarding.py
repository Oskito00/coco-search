from __future__ import annotations

from typing import Any, Protocol

from app.searches.definitions import SavedSearch
from app.searches.execution import create_ebay_client
from app.searches.mapping import to_ebay_search_params
from app.searches.sampling import diverse_items
from app.searches.validation import ensure_valid_saved_search
from app.utils.text_helpers import filter_items_by_keywords

DEFAULT_PREVIEW_LIMIT = 20
MAX_CANDIDATES = 100


class EbayPreviewClient(Protocol):
    """Public eBay client methods used for onboarding previews."""

    def search_item_summaries(
        self,
        keywords: str,
        filters: dict[str, Any] | None = None,
        limit: int = MAX_CANDIDATES,
        offset: int = 0,
        sort_order: str | None = None,
        marketplace: str | None = None,
    ) -> dict[str, Any]:
        """Fetch raw item summaries from eBay."""
        ...

    def parse_item_summary_response(
        self, response: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Parse eBay item summaries into app item dictionaries."""
        ...


class SearchOnboardingService:
    """Build labelled-training previews for saved searches."""

    def __init__(self, ebay_client_factory=create_ebay_client) -> None:
        self.ebay_client_factory = ebay_client_factory

    def create_preview(
        self, saved_search: SavedSearch, limit: int = DEFAULT_PREVIEW_LIMIT
    ) -> list[dict[str, Any]]:
        """Return diverse candidate dicts ready for likely/not-likely labels."""

        ensure_valid_saved_search(saved_search)
        if limit <= 0:
            return []

        candidate_limit = _candidate_limit(limit)
        candidates = self._fetch_candidates(saved_search, candidate_limit)
        filtered = filter_items_by_keywords(
            candidates,
            saved_search.filters.required_keywords,
            saved_search.filters.excluded_keywords,
        )
        selected = diverse_items(filtered, limit)
        return [_preview_item(saved_search.id, item) for item in selected]

    def _fetch_candidates(
        self, saved_search: SavedSearch, candidate_limit: int
    ) -> list[dict[str, Any]]:
        client = self.ebay_client_factory()
        params = to_ebay_search_params(saved_search)
        raw_response = client.search_item_summaries(
            keywords=params["keywords"],
            filters=params["filters"],
            limit=candidate_limit,
            offset=0,
            sort_order="newlyListed",
            marketplace=params["marketplace"],
        )
        return client.parse_item_summary_response(raw_response)


def _candidate_limit(limit: int) -> int:
    if limit <= 0:
        return 0
    return min(max(limit * 5, limit), MAX_CANDIDATES)


def _preview_item(search_id: str, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "search_id": search_id,
        "item_id": item.get("ebay_id") or item.get("item_id"),
        "title": item.get("title"),
        "price": item.get("price"),
        "currency": item.get("currency"),
        "condition": item.get("condition"),
        "location": item.get("location"),
        "buying_options": item.get("buying_options"),
        "url": item.get("url"),
        "image_url": item.get("image_url"),
        "seller": item.get("seller"),
        "likely_to_buy": None,
        "not_likely_to_buy": None,
    }
