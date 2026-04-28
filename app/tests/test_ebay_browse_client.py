from typing import Any

from ebay_client.browse.client import EbayBrowseClient


class FakeTokenProvider:
    """Token provider that avoids live eBay auth in Browse client tests."""

    def __init__(self, token: str = "test-token") -> None:
        self.token = token

    def get_token(self) -> str:
        """Return a deterministic OAuth token."""
        return self.token


class FakeResponse:
    """Minimal response object for offline Browse client tests."""

    def __init__(
        self,
        *,
        json_data: dict[str, Any],
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._json_data = json_data
        self.status_code = status_code
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:
        """Return the configured response body."""
        return self._json_data

    def raise_for_status(self) -> None:
        """Raise for HTTP errors."""
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Requests-like session that records outgoing calls."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str],
        params: dict[str, str | int],
    ) -> FakeResponse:
        """Record a GET call and return the next fake response."""
        self.calls.append({"url": url, "headers": headers, "params": params})
        return self.responses.pop(0)


def fake_item(item_id: str) -> dict[str, Any]:
    """Build a minimal eBay item summary accepted by the parser."""
    return {
        "itemId": item_id,
        "title": f"Item {item_id}",
        "price": {"value": "12.50", "currency": "GBP"},
        "buyingOptions": ["FIXED_PRICE"],
    }


def test_search_item_summaries_builds_headers_and_params() -> None:
    session = FakeSession([FakeResponse(json_data={"itemSummaries": []})])
    client = EbayBrowseClient(
        token_provider=FakeTokenProvider(),
        session=session,
        sleeper=lambda _: None,
    )

    client.search_item_summaries(
        "pokemon",
        filters={
            "min_price": 10,
            "max_price": 20,
            "buying_options": "FIXED_PRICE",
            "condition": "NEW",
            "item_location": "GB",
        },
        limit=50,
        offset=100,
        sort_order="price",
    )

    call = session.calls[0]
    assert call["url"].endswith("/item_summary/search")
    assert call["headers"] == {
        "Authorization": "Bearer test-token",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY-GB",
        "X-EBAY-C-CURRENCY": "GBP",
        "Content-Language": "en-GB",
        "Accept-Language": "en-GB",
        "Content-Type": "application/json",
    }
    assert call["params"] == {
        "q": "pokemon",
        "limit": 50,
        "offset": 100,
        "sort": "price",
        "filter": (
            "itemLocationCountry:GB,buyingOptions:{FIXED_PRICE},"
            "conditions:{NEW},priceCurrency:GBP,price:[10..20]"
        ),
    }


def test_search_item_summaries_applies_marketplace_override() -> None:
    session = FakeSession([FakeResponse(json_data={"itemSummaries": []})])
    client = EbayBrowseClient(
        token_provider=FakeTokenProvider(),
        session=session,
        sleeper=lambda _: None,
    )

    client.search_item_summaries(
        "iphone",
        filters={"item_location": "any", "min_price": 100},
        marketplace="EBAY_US",
    )

    call = session.calls[0]
    assert client.marketplace == "EBAY_US"
    assert client.country_code == "US"
    assert client.currency == "USD"
    assert call["headers"]["X-EBAY-C-MARKETPLACE-ID"] == "EBAY-US"
    assert call["headers"]["X-EBAY-C-CURRENCY"] == "USD"
    assert call["headers"]["Content-Language"] == "en-US"
    assert call["params"]["filter"] == "priceCurrency:USD,price:[100..]"


def test_search_item_summaries_retries_429_with_retry_after() -> None:
    sleep_calls: list[float] = []
    session = FakeSession(
        [
            FakeResponse(
                json_data={"error": "rate limited"},
                status_code=429,
                headers={"Retry-After": "2"},
            ),
            FakeResponse(json_data={"itemSummaries": []}),
        ]
    )
    client = EbayBrowseClient(
        token_provider=FakeTokenProvider(),
        session=session,
        sleeper=sleep_calls.append,
        rate_limit_retries=1,
    )

    assert client.search_item_summaries("pokemon") == {"itemSummaries": []}

    assert sleep_calls == [2]
    assert len(session.calls) == 2


def test_search_items_stops_when_page_is_short() -> None:
    sleep_calls: list[float] = []
    session = FakeSession(
        [
            FakeResponse(
                json_data={"itemSummaries": [fake_item("one"), fake_item("two")]}
            )
        ]
    )
    client = EbayBrowseClient(
        token_provider=FakeTokenProvider(),
        session=session,
        sleeper=sleep_calls.append,
    )

    items = client.search_items("pokemon", max_pages=None)

    assert [item["ebay_id"] for item in items] == ["one", "two"]
    assert sleep_calls == [1.0]
    assert len(session.calls) == 1
    assert session.calls[0]["params"]["offset"] == 0


def test_search_items_dedupes_across_pages() -> None:
    first_page = [fake_item(str(index)) for index in range(200)]
    second_page = [fake_item("199"), fake_item("200")]
    session = FakeSession(
        [
            FakeResponse(json_data={"itemSummaries": first_page}),
            FakeResponse(json_data={"itemSummaries": second_page}),
        ]
    )
    client = EbayBrowseClient(
        token_provider=FakeTokenProvider(),
        session=session,
        sleeper=lambda _: None,
    )

    items = client.search_items("pokemon", max_pages=None)
    item_ids = [item["ebay_id"] for item in items]

    assert len(items) == 201
    assert item_ids.count("199") == 1
    assert item_ids[-1] == "200"
    assert [call["params"]["offset"] for call in session.calls] == [0, 200]
