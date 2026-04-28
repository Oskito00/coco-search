from typing import Mapping, Optional, TypedDict

from ebay_client.browse.client import EbayBrowseClient


class RecordedCall(TypedDict):
    """Captured GET call details."""

    url: str
    headers: dict[str, str]
    params: dict[str, object]


class FakeTokenProvider:
    """Token provider used by offline Browse client tests."""

    def __init__(self, token: str = "test-token") -> None:
        self.token = token

    def get_token(self) -> str:
        """Return the configured fake token."""
        return self.token


class FakeResponse:
    """Small response double with the parts used by EbayBrowseClient."""

    def __init__(
        self,
        status_code: int = 200,
        json_data: Optional[dict[str, object]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.status_code = status_code
        self._json_data = json_data or {}
        self.headers = dict(headers or {})

    def json(self) -> dict[str, object]:
        """Return the fake JSON payload."""
        return self._json_data

    def raise_for_status(self) -> None:
        """Raise a runtime error for non-successful fake responses."""
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class RecordingSession:
    """Session double that records GET requests and returns queued responses."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[RecordedCall] = []

    def mount(self, prefix: str, adapter: object) -> None:
        """Accept adapter mounting to match requests.Session."""

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object],
    ) -> FakeResponse:
        """Record a GET call and return the next fake response."""
        self.calls.append(
            {
                "url": url,
                "headers": dict(headers),
                "params": dict(params),
            }
        )
        return self.responses.pop(0)


def item_summary(item_id: str) -> dict[str, object]:
    """Build a minimal item summary payload for parser-driven tests."""
    return {
        "itemId": item_id,
        "title": f"Item {item_id}",
        "price": {"value": "10.00", "currency": "GBP"},
    }


def test_search_item_summaries_sends_headers_and_params() -> None:
    session = RecordingSession([FakeResponse(json_data={"itemSummaries": []})])
    client = EbayBrowseClient(FakeTokenProvider(), session=session)

    client.search_item_summaries(
        "charizard",
        filters={"min_price": 10, "item_location": "any"},
        limit=25,
        offset=50,
        sort_order="price",
    )

    call = session.calls[0]
    assert call["url"] == "https://api.ebay.com/buy/browse/v1/item_summary/search"
    assert call["headers"] == {
        "Authorization": "Bearer test-token",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY-GB",
        "X-EBAY-C-CURRENCY": "GBP",
        "Content-Language": "en-GB",
        "Accept-Language": "en-GB",
        "Content-Type": "application/json",
    }
    assert call["params"] == {
        "q": "charizard",
        "limit": 25,
        "offset": 50,
        "sort": "price",
        "filter": "priceCurrency:GBP,price:[10..]",
    }


def test_search_item_summaries_applies_marketplace_override() -> None:
    session = RecordingSession([FakeResponse(json_data={"itemSummaries": []})])
    client = EbayBrowseClient(FakeTokenProvider(), session=session)

    client.search_item_summaries("laptop", marketplace="EBAY_US")

    headers = session.calls[0]["headers"]
    assert client.marketplace == "EBAY_US"
    assert client.country_code == "US"
    assert client.currency == "USD"
    assert headers["X-EBAY-C-MARKETPLACE-ID"] == "EBAY-US"
    assert headers["X-EBAY-C-CURRENCY"] == "USD"
    assert headers["Content-Language"] == "en-US"


def test_search_item_summaries_retries_429_once_after_retry_after() -> None:
    session = RecordingSession(
        [
            FakeResponse(status_code=429, headers={"Retry-After": "7"}),
            FakeResponse(json_data={"itemSummaries": []}),
        ]
    )
    sleep_calls: list[float] = []
    client = EbayBrowseClient(
        FakeTokenProvider(),
        session=session,
        retry_sleep=sleep_calls.append,
    )

    client.search_item_summaries("pikachu")

    assert len(session.calls) == 2
    assert sleep_calls == [7]


def test_search_items_stops_after_short_page() -> None:
    session = RecordingSession(
        [
            FakeResponse(
                json_data={
                    "itemSummaries": [item_summary(str(index)) for index in range(199)]
                }
            ),
            FakeResponse(json_data={"itemSummaries": [item_summary("extra")]}),
        ]
    )
    client = EbayBrowseClient(
        FakeTokenProvider(),
        session=session,
        page_sleep=lambda seconds: None,
    )

    items = client.search_items("books", max_pages=None)

    assert len(items) == 199
    assert len(session.calls) == 1


def test_search_items_dedupes_across_pages() -> None:
    session = RecordingSession(
        [
            FakeResponse(
                json_data={
                    "itemSummaries": [item_summary(str(index)) for index in range(200)]
                }
            ),
            FakeResponse(
                json_data={
                    "itemSummaries": [
                        item_summary("5"),
                        item_summary("200"),
                    ]
                }
            ),
        ]
    )
    client = EbayBrowseClient(
        FakeTokenProvider(),
        session=session,
        page_sleep=lambda seconds: None,
    )

    items = client.search_items("books", max_pages=None)

    assert len(items) == 201
    assert [item["ebay_id"] for item in items].count("5") == 1
    assert session.calls[1]["params"]["offset"] == 200
