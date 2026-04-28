from threading import local

from circuitbreaker import circuit

from ebay_client import EbayClient
from app.utils.text_helpers import filter_items_by_keywords


_thread_local = local()


def create_ebay_client():
    if not hasattr(_thread_local, "ebay_client"):
        _thread_local.ebay_client = EbayClient()
    return _thread_local.ebay_client


class EbaySearchExecutor:
    def __init__(self, api_factory=create_ebay_client):
        self.api_factory = api_factory

    def execute(
        self,
        keywords,
        filters=None,
        marketplace="EBAY_GB",
        required_keywords=None,
        excluded_keywords=None,
        sort_order="newlyListed",
        max_pages=1,
    ):
        api = self.api_factory()
        items = api.search_items(
            keywords=keywords,
            filters=filters,
            sort_order=sort_order,
            max_pages=max_pages,
            marketplace=marketplace,
        )
        return filter_items_by_keywords(items, required_keywords, excluded_keywords)


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
