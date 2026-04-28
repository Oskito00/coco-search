import logging
import time
from typing import Callable, Mapping, Optional, cast

import requests

from ebay_client.browse.dto import SearchFilters
from ebay_client.browse.filters import SearchFilterBuilder
from ebay_client.browse.headers import build_browse_headers
from ebay_client.browse.pagination import collect_unique_paginated_items
from ebay_client.browse.parsers import parse_item_summary_response
from ebay_client.browse.request_params import (
    build_search_params,
    create_search_request,
)
from ebay_client.browse.retry import BrowseSession, get_with_rate_limit_retry
from ebay_client.marketplaces import get_marketplace

logger = logging.getLogger(__name__)
DEFAULT_SEARCH_LIMIT = 200


class EbayBrowseClient:
    """Official eBay Browse API client."""

    token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    base_url = "https://api.ebay.com/buy/browse/v1"

    def __init__(
        self,
        token_provider,
        marketplace: str = "EBAY_GB",
        session=None,
        retry_sleep: Callable[[float], None] = time.sleep,
        page_sleep: Callable[[float], None] = time.sleep,
        max_rate_limit_retries: int = 1,
    ) -> None:
        self.token_provider = token_provider
        self.marketplace = marketplace
        self.session = session or requests.Session()
        self.retry_sleep = retry_sleep
        self.page_sleep = page_sleep
        self.max_rate_limit_retries = max_rate_limit_retries

        adapter = requests.adapters.HTTPAdapter(
            pool_connections=30,
            pool_maxsize=200,
            max_retries=3,
        )
        self.session.mount("https://", adapter)
        self._set_marketplace_config(marketplace)

    def _set_marketplace_config(self, marketplace: str) -> None:
        self.marketplace = marketplace
        self.marketplace_config = get_marketplace(marketplace)
        self.country_code = self.marketplace_config.location
        self.currency = self.marketplace_config.currency

    def search_item_summaries(
        self,
        keywords: str,
        filters: Optional[Mapping[str, object]] = None,
        limit: int = DEFAULT_SEARCH_LIMIT,
        offset: int = 0,
        sort_order: Optional[str] = None,
        marketplace: Optional[str] = None,
    ) -> dict[str, object]:
        """Search eBay item summaries and return the raw Browse API response."""
        if marketplace:
            self._set_marketplace_config(marketplace)

        request = create_search_request(
            keywords=keywords,
            filters=filters,
            limit=limit,
            offset=offset,
            sort_order=sort_order,
        )
        token = self.token_provider.get_token()
        headers = build_browse_headers(
            token=token,
            marketplace=self.marketplace,
            marketplace_config=self.marketplace_config,
        )
        params = build_search_params(
            request=request,
            filter_value=self.build_filter(request.filters),
        )
        response = get_with_rate_limit_retry(
            cast(BrowseSession, self.session),
            f"{self.base_url}/item_summary/search",
            headers,
            params,
            max_retries=self.max_rate_limit_retries,
            sleeper=self.retry_sleep,
        )
        return response.json()

    def search_items(
        self,
        keywords: str,
        filters: Optional[Mapping[str, object]] = None,
        sort_order: Optional[str] = None,
        max_pages: Optional[int] = 1,
        marketplace: Optional[str] = None,
    ) -> list[dict[str, object]]:
        """Search and parse eBay items across pages, returning deduplicated items."""
        if marketplace:
            self._set_marketplace_config(marketplace)

        def fetch_page(offset: int) -> dict[str, object]:
            return self.search_item_summaries(
                keywords=keywords,
                filters=filters,
                limit=DEFAULT_SEARCH_LIMIT,
                offset=offset,
                sort_order=sort_order,
            )

        return collect_unique_paginated_items(
            fetch_page=fetch_page,
            parse_page=self.parse_item_summary_response,
            max_pages=max_pages,
            page_size=DEFAULT_SEARCH_LIMIT,
            sleeper=self.page_sleep,
        )

    def build_filter(self, filters: SearchFilters) -> str:
        """Build a Browse API filter expression for search filters."""
        return SearchFilterBuilder(self.currency).build(filters)

    def parse_item_summary_response(
        self,
        response: Mapping[str, object],
    ) -> list[dict[str, object]]:
        """Parse a raw item summary response using the active marketplace currency."""
        return parse_item_summary_response(response, default_currency=self.currency)
