from threading import local
from typing import Any, Callable, Optional

from circuitbreaker import circuit

from ebay_client import EbayClient
from app.searches.definitions import SavedSearch
from app.searches.mapping import to_ebay_search_params
from app.utils.text_helpers import filter_items_by_keywords

_thread_local = local()


def create_ebay_client() -> EbayClient:
    if not hasattr(_thread_local, "ebay_client"):
        _thread_local.ebay_client = EbayClient()
    return _thread_local.ebay_client


class EbaySearchExecutor:
    def __init__(
        self, api_factory: Callable[[], EbayClient] = create_ebay_client
    ) -> None:
        self.api_factory = api_factory

    def execute(
        self,
        keywords: str,
        filters: Optional[dict[str, Any]] = None,
        marketplace: str = "EBAY_GB",
        required_keywords: Optional[str] = None,
        excluded_keywords: Optional[str] = None,
        sort_order: str = "newlyListed",
        max_pages: int = 1,
    ) -> list[dict[str, Any]]:
        api = self.api_factory()
        items = api.search_items(
            keywords=keywords,
            filters=filters,
            sort_order=sort_order,
            max_pages=max_pages,
            marketplace=marketplace,
        )
        return filter_items_by_keywords(items, required_keywords, excluded_keywords)

    def execute_saved_search(
        self,
        saved_search: SavedSearch,
        sort_order: str = "newlyListed",
        max_pages: int = 1,
    ) -> list[dict[str, Any]]:
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
def scrape_ebay(
    keywords,
    filters=None,
    marketplace="EBAY_GB",
    required_keywords=None,
    excluded_keywords=None,
):
    return EbaySearchExecutor().execute(
        keywords=keywords,
        filters=filters,
        marketplace=marketplace,
        required_keywords=required_keywords,
        excluded_keywords=excluded_keywords,
    )


def scrape_new_items(
    keywords,
    filters=None,
    marketplace="EBAY_GB",
    required_keywords=None,
    excluded_keywords=None,
):
    return EbaySearchExecutor().execute(
        keywords=keywords,
        filters=filters,
        marketplace=marketplace,
        required_keywords=required_keywords,
        excluded_keywords=excluded_keywords,
    )
