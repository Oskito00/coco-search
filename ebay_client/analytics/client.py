from typing import Any

import requests

from ebay_client.analytics.rate_limits import extract_browse_rate


class EbayAnalyticsClient:
    """Client for eBay developer analytics endpoints."""

    rate_limit_url = "https://api.ebay.com/developer/analytics/v1_beta/rate_limit"

    def __init__(self, token_provider: Any, session: Any | None = None) -> None:
        """Create an analytics client with a token provider and HTTP session."""
        self.token_provider = token_provider
        self.session = session or requests.Session()

    def get_rate_limits(self) -> dict[str, Any]:
        """Fetch rate limit data from the eBay analytics API."""
        token = self.token_provider.get_token()
        response = self.session.get(
            self.rate_limit_url,
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code == 403:
            raise ValueError("Missing required scope")

        response.raise_for_status()
        return response.json()

    def get_browse_limits(
        self, rate_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Return Browse API rate limits from provided or fetched rate data."""
        return extract_browse_rate(rate_data or self.get_rate_limits())

    def get_search_limits(
        self, rate_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Return search rate limits from provided or fetched rate data."""
        return extract_browse_rate(rate_data or self.get_rate_limits())
