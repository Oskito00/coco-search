"""Client for eBay Developer Analytics endpoints."""

from typing import Any, Protocol

import requests  # type: ignore[import-untyped]

from ebay_client.analytics.rate_limits import extract_browse_rate


class _AnalyticsResponse(Protocol):
    """Protocol for response objects returned by requests-like sessions."""

    status_code: int

    def json(self) -> dict[str, Any]:
        """Return decoded response JSON."""
        ...

    def raise_for_status(self) -> None:
        """Raise for non-successful HTTP statuses."""
        ...


class _AnalyticsSession(Protocol):
    """Protocol for session objects used by the analytics client."""

    def get(self, url: str, headers: dict[str, str]) -> _AnalyticsResponse:
        """Send a GET request."""
        ...


class EbayAnalyticsClient:
    """Fetch eBay developer analytics rate-limit data."""

    DEFAULT_BASE_URL = "https://api.ebay.com/developer/analytics/v1_beta"

    def __init__(
        self,
        access_token: str | None = None,
        *,
        token: str | None = None,
        session: _AnalyticsSession | None = None,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        """Create an analytics client.

        ``token`` is accepted as a compatibility alias for ``access_token``.
        """
        self.access_token = access_token or token
        self.session = session or requests.Session()
        self.base_url = base_url.rstrip("/")

    def get_rate_limits(self) -> dict[str, Any]:
        """Fetch raw eBay API rate-limit data."""
        response = self.session.get(
            f"{self.base_url}/rate_limit",
            headers=self._headers(),
        )
        if response.status_code == 403:
            raise ValueError("Missing required scope")

        response.raise_for_status()
        return response.json()

    def get_browse_limits(self) -> dict[str, Any]:
        """Return the first Browse API rate-limit record."""
        return extract_browse_rate(self.get_rate_limits())

    def get_search_limits(self) -> dict[str, Any]:
        """Return search-related limits, currently backed by Browse limits."""
        return extract_browse_rate(self.get_rate_limits())

    def _headers(self) -> dict[str, str]:
        """Build request headers for the analytics API."""
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}
