from typing import Any

import pytest

from ebay_client.analytics.client import EbayAnalyticsClient
from ebay_client.analytics.rate_limits import extract_browse_rate


class FakeResponse:
    """Small response double for analytics client tests."""

    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self.payload = payload
        self.raise_called = False

    def json(self) -> dict[str, Any]:
        """Return the configured JSON payload."""
        return self.payload

    def raise_for_status(self) -> None:
        """Track that status handling was delegated to the response."""
        self.raise_called = True


class FakeSession:
    """Small session double that records the outgoing analytics request."""

    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.last_url: str | None = None
        self.last_headers: dict[str, str] | None = None

    def get(self, url: str, headers: dict[str, str]) -> FakeResponse:
        """Return the configured response and capture request details."""
        self.last_url = url
        self.last_headers = headers
        return self.response


RATE_LIMIT_PAYLOAD = {
    "rateLimits": [
        {
            "apiContext": "sell",
            "apiName": "Inventory",
            "resources": [],
        },
        {
            "apiContext": "buy",
            "apiName": "Browse",
            "resources": [
                {"name": "buy.other", "rates": [{"limit": 1}]},
                {
                    "name": "buy.browse",
                    "rates": [
                        {
                            "limit": 5000,
                            "remaining": 4999,
                            "reset": "2026-04-29T00:00:00.000Z",
                        }
                    ],
                },
            ],
        },
    ]
}


def test_get_rate_limits_raises_for_missing_scope() -> None:
    response = FakeResponse(status_code=403, payload={})
    client = EbayAnalyticsClient(access_token="token", session=FakeSession(response))

    with pytest.raises(ValueError, match="Missing required scope"):
        client.get_rate_limits()

    assert response.raise_called is False


def test_get_browse_limits_extracts_first_browse_rate() -> None:
    response = FakeResponse(status_code=200, payload=RATE_LIMIT_PAYLOAD)
    session = FakeSession(response)
    client = EbayAnalyticsClient(access_token="token", session=session)

    assert client.get_browse_limits() == {
        "limit": 5000,
        "remaining": 4999,
        "reset": "2026-04-29T00:00:00.000Z",
    }
    assert session.last_url == (
        "https://api.ebay.com/developer/analytics/v1_beta/rate_limit"
    )
    assert session.last_headers == {"Authorization": "Bearer token"}
    assert response.raise_called is True


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"rateLimits": []},
        {"rateLimits": [{"apiContext": "sell", "apiName": "Browse"}]},
        {
            "rateLimits": [
                {
                    "apiContext": "buy",
                    "apiName": "Browse",
                    "resources": [{"name": "buy.other", "rates": [{"limit": 1}]}],
                }
            ]
        },
        {
            "rateLimits": [
                {
                    "apiContext": "buy",
                    "apiName": "Browse",
                    "resources": [{"name": "buy.browse", "rates": []}],
                }
            ]
        },
    ],
)
def test_extract_browse_rate_returns_empty_dict_for_missing_paths(
    payload: dict[str, Any],
) -> None:
    assert extract_browse_rate(payload) == {}


def test_get_search_limits_uses_browse_rate_limits() -> None:
    response = FakeResponse(status_code=200, payload=RATE_LIMIT_PAYLOAD)
    client = EbayAnalyticsClient(access_token="token", session=FakeSession(response))

    assert client.get_search_limits()["limit"] == 5000
