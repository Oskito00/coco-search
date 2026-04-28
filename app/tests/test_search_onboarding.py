from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.searches.definitions import SavedSearch, SearchFilters, SearchSchedule
from app.searches.onboarding import SearchOnboardingService


@dataclass
class FakeEbayClient:
    items: list[dict[str, Any]]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def search_item_summaries(
        self,
        keywords: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
        sort_order: str | None = None,
        marketplace: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "keywords": keywords,
                "filters": filters,
                "limit": limit,
                "offset": offset,
                "sort_order": sort_order,
                "marketplace": marketplace,
            }
        )
        return {"items": self.items[:limit]}

    def parse_item_summary_response(
        self, response: dict[str, Any]
    ) -> list[dict[str, Any]]:
        return list(response["items"])


def test_create_preview_filters_legacy_keywords_and_labels_items() -> None:
    fake_client = FakeEbayClient(
        items=[
            _item("1", "Sony Alpha camera body", 100, "USED", "GB"),
            _item("2", "Sony Alpha camera body boxed", 110, "USED", "GB"),
            _item("3", "Sony Alpha camera lens", 300, "NEW", "US"),
            _item("4", "Sony Alpha camera broken", 50, "USED", "GB"),
            _item("5", "Canon camera body", 150, "USED", "GB"),
            _item("6", "Sony Alpha camera kit", 500, "NEW", "DE"),
        ]
    )
    service = SearchOnboardingService(ebay_client_factory=lambda: fake_client)

    preview = service.create_preview(_saved_search(), limit=3)

    assert fake_client.calls[0]["limit"] == 15
    assert fake_client.calls[0]["marketplace"] == "EBAY_GB"
    assert [item["item_id"] for item in preview] == ["1", "3", "6"]
    assert all(item["likely_to_buy"] is None for item in preview)
    assert all(item["not_likely_to_buy"] is None for item in preview)


def test_create_preview_fetches_at_most_one_hundred_candidates() -> None:
    fake_client = FakeEbayClient(
        items=[
            _item(str(index), f"Sony camera {index}", index, "USED", "GB")
            for index in range(150)
        ]
    )
    service = SearchOnboardingService(ebay_client_factory=lambda: fake_client)

    service.create_preview(_saved_search(), limit=25)

    assert fake_client.calls[0]["limit"] == 100


def _saved_search() -> SavedSearch:
    return SavedSearch(
        id="search-1",
        user_id=7,
        keyword_id=11,
        keywords="sony camera",
        marketplace="EBAY_GB",
        is_active=True,
        filters=SearchFilters(
            min_price=Decimal("50"),
            max_price=Decimal("500"),
            item_location="GB",
            condition="USED",
            buying_options="FIXED_PRICE|AUCTION",
            required_keywords="sony, camera",
            excluded_keywords="broken, canon",
        ),
        schedule=SearchSchedule(check_interval=5),
    )


def _item(
    item_id: str,
    title: str,
    price: int,
    condition: str,
    country: str,
) -> dict[str, Any]:
    return {
        "ebay_id": item_id,
        "title": title,
        "price": price,
        "currency": "GBP",
        "condition": condition,
        "location": {"country": country},
        "buying_options": "FIXED_PRICE",
        "url": f"https://example.test/{item_id}",
        "image_url": f"https://example.test/{item_id}.jpg",
        "seller": "seller",
    }
