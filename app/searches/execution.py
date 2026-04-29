"""Low-level eBay search execution for saved searches.

This module owns the bridge between :class:`SavedSearch` domain objects and
the ``ebay_client`` SDK. Higher-level cadence concerns (recent vs. full
scrapes) live in :mod:`app.searches.strategies`.
"""

from __future__ import annotations

from threading import local
from typing import Any, Callable, Optional

from circuitbreaker import circuit

from app.searches.definitions import SavedSearch
from app.searches.mapping import to_ebay_search_params
from app.utils.text_helpers import filter_items_by_keywords
from ebay_client import EbayClient

_thread_local = local()


def create_ebay_client() -> EbayClient:
    """Return a thread-local ``EbayClient`` so we reuse OAuth tokens per worker."""
    if not hasattr(_thread_local, "ebay_client"):
        _thread_local.ebay_client = EbayClient()
    return _thread_local.ebay_client


class EbaySearchExecutor:
    """Run eBay searches and apply post-fetch keyword gates."""

    def __init__(
        self,
        api_factory: Callable[[], EbayClient] = create_ebay_client,
    ) -> None:
        self.api_factory = api_factory

    def execute(
        self,
        keywords: str,
        filters: Optional[dict[str, Any]] = None,
        marketplace: str = "EBAY_GB",
        required_keywords: Optional[str] = None,
        excluded_keywords: Optional[str] = None,
        sort_order: Optional[str] = "newlyListed",
        max_pages: int = 1,
    ) -> list[dict[str, Any]]:
        """Run a parametric search and apply hard keyword filters."""
        items = self._search(
            keywords=keywords,
            filters=filters,
            marketplace=marketplace,
            sort_order=sort_order,
            max_pages=max_pages,
        )
        return _circuit_protected_filter(items, required_keywords, excluded_keywords)

    def execute_saved_search(
        self,
        saved_search: SavedSearch,
        sort_order: Optional[str] = "newlyListed",
        max_pages: int = 1,
    ) -> list[dict[str, Any]]:
        """Run an eBay search defined by a :class:`SavedSearch`."""
        params = to_ebay_search_params(saved_search)
        return self.execute(
            keywords=params["keywords"],
            filters=params["filters"],
            marketplace=params["marketplace"],
            required_keywords=saved_search.filters.required_keywords,
            excluded_keywords=saved_search.filters.excluded_keywords,
            sort_order=sort_order,
            max_pages=max_pages,
        )

    @circuit(failure_threshold=3, recovery_timeout=60)
    def _search(
        self,
        keywords: str,
        filters: Optional[dict[str, Any]],
        marketplace: str,
        sort_order: Optional[str],
        max_pages: int,
    ) -> list[dict[str, Any]]:
        """Wrap the SDK call so circuit-breaker state lives on the executor."""
        api = self.api_factory()
        return api.search_items(
            keywords=keywords,
            filters=filters,
            sort_order=sort_order,
            max_pages=max_pages,
            marketplace=marketplace,
        )


def _circuit_protected_filter(
    items: list[dict[str, Any]],
    required_keywords: Optional[str],
    excluded_keywords: Optional[str],
) -> list[dict[str, Any]]:
    """Apply hard keyword filters; kept as a free function so the executor stays small."""
    return filter_items_by_keywords(items, required_keywords, excluded_keywords)
