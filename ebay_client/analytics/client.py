import requests

from ebay_client.analytics.rate_limits import extract_browse_rate


class EbayAnalyticsClient:
    rate_limit_url = "https://api.ebay.com/developer/analytics/v1_beta/rate_limit"

    def __init__(self, token_provider, session=None):
        self.token_provider = token_provider
        self.session = session or requests.Session()

    def get_rate_limits(self):
        token = self.token_provider.get_token()
        response = self.session.get(
            self.rate_limit_url,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 403:
            raise ValueError("Missing required scope")

        response.raise_for_status()
        return response.json()

    def get_browse_limits(self, rate_data=None):
        return extract_browse_rate(rate_data or self.get_rate_limits())

    def get_search_limits(self, rate_data=None):
        return extract_browse_rate(rate_data or self.get_rate_limits())
