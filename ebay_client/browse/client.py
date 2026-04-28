import logging
import time

import requests

from ebay_client.browse.dto import SearchFilters, SearchRequest
from ebay_client.browse.filters import SearchFilterBuilder
from ebay_client.browse.parsers import parse_item_summary_response
from ebay_client.browse.responses import dedupe_items
from ebay_client.marketplaces import get_marketplace


logger = logging.getLogger(__name__)


class EbayBrowseClient:
    """Official eBay Browse API client."""

    token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    base_url = "https://api.ebay.com/buy/browse/v1"

    def __init__(self, token_provider, marketplace="EBAY_GB", session=None):
        self.token_provider = token_provider
        self.marketplace = marketplace
        self.session = session or requests.Session()

        adapter = requests.adapters.HTTPAdapter(
            pool_connections=30,
            pool_maxsize=200,
            max_retries=3,
        )
        self.session.mount("https://", adapter)
        self._set_marketplace_config(marketplace)

    def _set_marketplace_config(self, marketplace):
        self.marketplace = marketplace
        self.marketplace_config = get_marketplace(marketplace)
        self.country_code = self.marketplace_config.location
        self.currency = self.marketplace_config.currency

    def search_item_summaries(
        self,
        keywords,
        filters=None,
        limit=200,
        offset=0,
        sort_order=None,
        marketplace=None,
    ):
        if marketplace:
            self._set_marketplace_config(marketplace)

        request = SearchRequest(
            keywords=keywords,
            filters=SearchFilters.from_mapping(filters),
            limit=limit,
            offset=offset,
            sort_order=sort_order,
        )
        token = self.token_provider.get_token()
        marketplace_header = self.marketplace.replace("_", "-")

        headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": marketplace_header,
            "X-EBAY-C-CURRENCY": self.currency,
            "Content-Language": self.marketplace_config.language,
            "Accept-Language": self.marketplace_config.language,
            "Content-Type": "application/json",
        }
        params = {
            "q": request.keywords,
            "limit": request.limit,
            "offset": request.offset,
        }

        if request.sort_order:
            params["sort"] = request.sort_order

        filter_value = self.build_filter(request.filters)
        if filter_value:
            params["filter"] = filter_value

        response = self.session.get(
            f"{self.base_url}/item_summary/search",
            headers=headers,
            params=params,
        )

        if response.status_code == 429:
            sleep_time = int(response.headers.get("Retry-After", 60))
            time.sleep(sleep_time)
            return self.search_item_summaries(
                keywords,
                filters,
                limit,
                offset,
                sort_order,
                marketplace,
            )

        response.raise_for_status()
        return response.json()

    def search_items(
        self,
        keywords,
        filters=None,
        sort_order=None,
        max_pages=1,
        marketplace=None,
    ):
        if marketplace:
            self._set_marketplace_config(marketplace)

        returned_items = []
        pages_searched = 0
        offset = 0

        while max_pages is None or pages_searched < max_pages:
            time.sleep(1)
            raw_response = self.search_item_summaries(
                keywords=keywords,
                filters=filters,
                limit=200,
                offset=offset,
                sort_order=sort_order,
            )
            parsed_items = self.parse_item_summary_response(raw_response)
            returned_items.extend(parsed_items)

            offset += len(parsed_items)
            pages_searched += 1
            if len(parsed_items) < 200:
                break

        return dedupe_items(returned_items)

    def build_filter(self, filters):
        return SearchFilterBuilder(self.currency).build(filters)

    def parse_item_summary_response(self, response):
        return parse_item_summary_response(response, default_currency=self.currency)
