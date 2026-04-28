from typing import Any
from unittest.mock import Mock

import pytest

from ebay_client.analytics.client import EbayAnalyticsClient
from ebay_client.analytics.rate_limits import extract_browse_rate


def _rate_limit_payload(rate: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a minimal eBay analytics payload for Browse rate limit tests."""
    browse_rate = {"limit": 5000, "remaining": 2500} if rate is None else rate
    return {
        "rateLimits": [
            {
                "apiContext": "buy",
                "apiName": "Browse",
                "resources": [
                    {
                        "name": "buy.browse",
                        "rates": [browse_rate],
                    }
                ],
            }
        ]
    }


def test_extract_browse_rate_returns_first_matching_rate() -> None:
    rate = {"limit": 5000, "remaining": 2499, "reset": "2026-04-29T00:00:00.000Z"}

    assert extract_browse_rate(_rate_limit_payload(rate)) == rate


def test_extract_browse_rate_preserves_empty_rate() -> None:
    assert extract_browse_rate(_rate_limit_payload({})) == {}


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
                    "resources": [{"name": "buy.browse"}],
                }
            ]
        },
    ],
)
def test_extract_browse_rate_returns_empty_dict_when_missing(
    payload: dict[str, Any],
) -> None:
    assert extract_browse_rate(payload) == {}


def test_analytics_client_raises_for_missing_scope() -> None:
    token_provider = Mock()
    token_provider.get_token.return_value = "access-token"
    response = Mock(status_code=403)
    session = Mock()
    session.get.return_value = response
    client = EbayAnalyticsClient(token_provider=token_provider, session=session)

    with pytest.raises(ValueError, match="Missing required scope"):
        client.get_rate_limits()

    response.raise_for_status.assert_not_called()


def test_analytics_client_get_browse_limits_extracts_successful_response() -> None:
    token_provider = Mock()
    token_provider.get_token.return_value = "access-token"
    response = Mock(status_code=200)
    response.json.return_value = _rate_limit_payload({"limit": 100, "remaining": 50})
    session = Mock()
    session.get.return_value = response
    client = EbayAnalyticsClient(token_provider=token_provider, session=session)

    assert client.get_browse_limits() == {"limit": 100, "remaining": 50}
    session.get.assert_called_once_with(
        client.rate_limit_url,
        headers={"Authorization": "Bearer access-token"},
    )
    response.raise_for_status.assert_called_once_with()
