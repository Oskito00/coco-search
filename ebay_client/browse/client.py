import logging
import time
from collections.abc import Callable, Mapping
from typing import Any

import requests  # type: ignore[import-untyped]

from ebay_client.browse.filters import SearchFilterBuilder
from ebay_client.browse.headers import build_browse_headers
from ebay_client.browse.pagination import collect_search_items
from ebay_client.browse.parsers import parse_item_summary_response
from ebay_client.browse.search_requests import (
    build_search_params,
    create_search_request,
)
from ebay_client.browse.transport import fetch_json_with_retry
from ebay_client.marketplaces import get_marketplace

logger = logging.getLogger(__name__)


class EbayBrowseClient:
    """Official eBay Browse API client."""

    token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    base_url = "https://api.ebay.com/buy/browse/v1"

    def __init__(
        self,
        token_provider: Any,
        marketplace: str = "EBAY_GB",
        session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
        rate_limit_retries: int = 3,
    ) -> None:
        self.token_provider = token_provider
        self.marketplace = marketplace
        self.session = session or requests.Session()
        self.sleeper = sleeper
        self.rate_limit_retries = rate_limit_retries

        self._configure_session(self.session)
        self._set_marketplace_config(marketplace)

    @staticmethod
    def _configure_session(session: requests.Session) -> None:
        """Apply connection pooling to real requests sessions."""
        if not hasattr(session, "mount"):
            return

        adapter = requests.adapters.HTTPAdapter(
            pool_connections=30,
            pool_maxsize=200,
            max_retries=3,
        )
        session.mount("https://", adapter)

    def _set_marketplace_config(self, marketplace: str) -> None:
        self.marketplace = marketplace
        self.marketplace_config = get_marketplace(marketplace)
        self.country_code = self.marketplace_config.location
        self.currency = self.marketplace_config.currency

    def search_item_summaries(
        self,
        keywords,
        filters=None,
        limit: int = 200,
        offset: int = 0,
        sort_order: str | None = None,
        marketplace: str | None = None,
    ) -> dict[str, Any]:
        if marketplace:
            self._set_marketplace_config(marketplace)

        request = create_search_request(
            keywords=keywords,
            filters=filters,
            limit=limit,
            offset=offset,
            sort_order=sort_order,
        )
        headers = self._build_headers()
        params = build_search_params(request, self.build_filter(request.filters))
        return fetch_json_with_retry(
            session=self.session,
            url=self._search_url(),
            headers=headers,
            params=params,
            max_retries=self.rate_limit_retries,
            sleeper=self.sleeper,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build authenticated headers for the current marketplace."""
        return build_browse_headers(
            token=self.token_provider.get_token(),
            marketplace=self.marketplace,
            currency=self.currency,
            language=self.marketplace_config.language,
        )

    def _search_url(self) -> str:
        """Return the Browse item summary search URL."""
        return f"{self.base_url}/item_summary/search"

    def search_items(
        self,
        keywords,
        filters=None,
        sort_order: str | None = None,
        max_pages: int | None = 1,
        marketplace: str | None = None,
    ) -> list[dict[str, Any]]:
        if marketplace:
            self._set_marketplace_config(marketplace)

        return collect_search_items(
            fetch_page=lambda offset, limit: self.search_item_summaries(
                keywords=keywords,
                filters=filters,
                limit=limit,
                offset=offset,
                sort_order=sort_order,
            ),
            parse_page=self.parse_item_summary_response,
            max_pages=max_pages,
            sleeper=self.sleeper,
        )

    def build_filter(self, filters) -> str:
        return SearchFilterBuilder(self.currency).build(filters)

    def parse_item_summary_response(
        self,
        response: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        return parse_item_summary_response(response, default_currency=self.currency)
