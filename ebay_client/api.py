from ebay_client.auth import EbayTokenProvider
from ebay_client.analytics import EbayAnalyticsClient
from ebay_client.browse import EbayBrowseClient
from ebay_client.config import load_ebay_credentials


class EbayClient:
    """SDK entry point for the eBay API endpoints used by Coco Search."""

    def __init__(
        self,
        marketplace="EBAY_GB",
        credentials=None,
        session=None,
        token_provider=None,
        token_store=None,
    ):
        self.credentials = credentials if credentials is not None else load_ebay_credentials()
        self.token_provider = token_provider or EbayTokenProvider(
            credentials=self.credentials,
            token_url=EbayBrowseClient.token_url,
            session=session,
            token_store=token_store,
        )
        self.browse = EbayBrowseClient(
            token_provider=self.token_provider,
            marketplace=marketplace,
            session=session,
        )
        self.analytics = EbayAnalyticsClient(
            token_provider=self.token_provider,
            session=session,
        )

    @property
    def marketplace(self):
        return self.browse.marketplace

    @property
    def marketplace_config(self):
        return self.browse.marketplace_config

    @property
    def country_code(self):
        return self.browse.country_code

    @property
    def currency(self):
        return self.browse.currency

    def search_item_summaries(
        self,
        keywords,
        filters=None,
        limit=200,
        offset=0,
        sort_order=None,
        marketplace=None,
    ):
        return self.browse.search_item_summaries(
            keywords=keywords,
            filters=filters,
            limit=limit,
            offset=offset,
            sort_order=sort_order,
            marketplace=marketplace,
        )

    def search_items(
        self,
        keywords,
        filters=None,
        sort_order=None,
        max_pages=1,
        marketplace=None,
    ):
        return self.browse.search_items(
            keywords=keywords,
            filters=filters,
            sort_order=sort_order,
            max_pages=max_pages,
            marketplace=marketplace,
        )

    def parse_item_summary_response(self, response):
        return self.browse.parse_item_summary_response(response)

    def get_rate_limits(self):
        return self.analytics.get_rate_limits()

    def get_browse_limits(self, rate_data=None):
        return self.analytics.get_browse_limits(rate_data)

    def get_search_limits(self, rate_data=None):
        return self.analytics.get_search_limits(rate_data)


__all__ = ["EbayClient"]
