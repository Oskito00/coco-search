from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

from app.searches import item_processor
from app.searches.events import (
    AUCTION_ENDING_SOON,
    ITEM_DISCOVERED,
    ITEM_UPDATED,
    PRICE_DROPPED,
    SearchProcessingResult,
)
from app.searches.item_processor import SearchItemProcessor, process_items


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class FakeRepository:
    def __init__(self) -> None:
        self.items_by_ebay_id: dict[str, Any] = {}
        self.query_links: dict[tuple[Any, Any], Any] = {}
        self.created_payloads: list[dict[str, Any]] = []
        self.observations: list[dict[str, Any]] = []
        self.events: list[Any] = []
        self.next_item_id = 1

    def get_by_ebay_id(self, ebay_id: str) -> Any | None:
        return self.items_by_ebay_id.get(ebay_id)

    def get_feedback(self, user_id: Any, item_id: Any, keyword_id: Any) -> None:
        return None

    def create_item(self, item_data: dict[str, Any]) -> Any:
        item = SimpleNamespace(item_id=self.next_item_id, **item_data)
        self.next_item_id += 1
        self.items_by_ebay_id[item.ebay_id] = item
        self.created_payloads.append(item_data)
        return item

    def link_keyword(self, keyword_id: Any, item_id: Any, found_at: Any = None) -> Any:
        return SimpleNamespace(
            keyword_id=keyword_id, item_id=item_id, found_at=found_at
        )

    def link_query(
        self, query_id: Any, item_id: Any, created_at: Any = None
    ) -> Any | None:
        key = (query_id, item_id)
        if key in self.query_links:
            return None
        link = SimpleNamespace(
            query_id=query_id,
            item_id=item_id,
            created_at=created_at,
            auction_ending_notification_sent=False,
        )
        self.query_links[key] = link
        return link

    def get_query_item(self, query_id: Any, item_id: Any) -> Any | None:
        return self.query_links.get((query_id, item_id))

    def update_item(
        self, item: Any, item_data: dict[str, Any], updated_at: datetime
    ) -> bool:
        changed = False
        for key, value in item_data.items():
            if key == "item_id" or not hasattr(item, key):
                continue
            if getattr(item, key) != value:
                setattr(item, key, value)
                changed = True
        if changed:
            item.last_updated = updated_at
        return changed

    def record_item_observation(self, observation: dict[str, Any]) -> None:
        self.observations.append(observation)

    def record_domain_event(self, event: Any) -> None:
        self.events.append(event)


class FakeNotifications:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    def notify_search_events(self, query: Any, result: SearchProcessingResult) -> None:
        self.calls.append((query, result))


class FakeCreateRepository:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> dict[str, Any]:
        self.created.append(kwargs)
        return kwargs


def test_processor_normalizes_raw_sdk_payload_and_records_new_item_event(
    monkeypatch: Any,
) -> None:
    session = FakeSession()
    monkeypatch.setattr(item_processor.db, "session", session)
    repository = FakeRepository()
    query = _query()

    raw_item = {
        "itemId": "v1|123",
        "legacyItemId": "123",
        "title": "Pokemon card",
        "price": {"value": "129.95", "currency": "GBP"},
        "itemWebUrl": "https://example.test/item",
        "image": {"imageUrl": "https://example.test/image.jpg"},
        "seller": {"username": "seller-one", "feedbackPercentage": "99.8"},
        "itemLocation": {"country": "GB", "postalCode": "SW1A"},
        "buyingOptions": ["FIXED_PRICE"],
        "listingMarketplaceId": "EBAY_GB",
    }

    result = SearchItemProcessor(
        item_repository=repository,
        event_repository=repository,
        observation_repository=repository,
        notification_service=FakeNotifications(),
    ).process([raw_item], query, notify=False)

    created_payload = repository.created_payloads[0]
    assert created_payload["ebay_id"] == "v1|123"
    assert created_payload["price"] == 129.95
    assert created_payload["location"] == {"country": "GB", "postal_code": "SW1A"}
    assert created_payload["location_country"] == "GB"
    assert result.new_items == [repository.items_by_ebay_id["v1|123"]]
    assert [event.event_type for event in result.domain_events] == [ITEM_DISCOVERED]
    assert repository.events == result.domain_events
    assert repository.observations[0]["price"] == 129.95
    assert session.committed is True


def test_processor_persists_domain_events_with_schema_fields(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(item_processor.db, "session", FakeSession())
    item_repository = FakeRepository()
    event_repository = FakeCreateRepository()
    query = _query()
    end_time = datetime.now(timezone.utc) + timedelta(hours=1)
    existing = SimpleNamespace(item_id=42, ebay_id="abc", price=100.0)
    item_repository.items_by_ebay_id["abc"] = existing
    item_repository.query_links[(query.query_id, existing.item_id)] = SimpleNamespace(
        auction_ending_notification_sent=False
    )

    result = SearchItemProcessor(
        item_repository=item_repository,
        event_repository=event_repository,
        observation_repository=item_repository,
        notification_service=FakeNotifications(),
    ).process(
        [{"ebay_id": "abc", "price": 75.0, "end_time": end_time}],
        query,
        notify=False,
    )

    assert [event.event_type for event in result.domain_events] == [
        ITEM_UPDATED,
        PRICE_DROPPED,
        AUCTION_ENDING_SOON,
    ]
    price_drop = event_repository.created[1]
    assert price_drop == {
        "event_type": PRICE_DROPPED,
        "aggregate_type": "item",
        "aggregate_id": existing.item_id,
        "user_id": query.user_id,
        "query_id": query.query_id,
        "item_id": existing.item_id,
        "payload": {"old_price": 100.0, "new_price": 75.0},
        "status": "pending",
        "source": "search_item_processor",
        "occurred_at": result.domain_events[1].occurred_at,
    }
    assert event_repository.created[2]["payload"] == {"end_time": end_time.isoformat()}


def test_processor_persists_observations_with_schema_fields(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(item_processor.db, "session", FakeSession())
    item_repository = FakeRepository()
    observation_repository = FakeCreateRepository()
    query = _query(search_run_id="run-1")
    end_time = datetime.now(timezone.utc) + timedelta(days=1)

    SearchItemProcessor(
        item_repository=item_repository,
        event_repository=item_repository,
        observation_repository=observation_repository,
        notification_service=FakeNotifications(),
    ).process(
        [
            {
                "ebay_id": "abc",
                "price": 50.0,
                "currency": "GBP",
                "current_bid": 25.0,
                "condition": "USED",
                "buying_options": '["AUCTION"]',
                "end_time": end_time,
            }
        ],
        query,
        notify=False,
    )

    observation = observation_repository.created[0]
    assert observation["item_id"] == item_repository.items_by_ebay_id["abc"].item_id
    assert observation["query_id"] == query.query_id
    assert observation["search_run_id"] == "run-1"
    assert observation["price"] == 50.0
    assert observation["currency"] == "GBP"
    assert observation["current_bid"] == 25.0
    assert observation["condition"] == "USED"
    assert observation["buying_options"] == '["AUCTION"]'
    assert observation["raw_item_snapshot"]["end_time"] == end_time.isoformat()
    assert observation["is_new_item"] is True
    assert observation["hard_filter_passed"] is True


def test_processor_records_update_and_price_drop_events(monkeypatch: Any) -> None:
    monkeypatch.setattr(item_processor.db, "session", FakeSession())
    repository = FakeRepository()
    query = _query()
    existing = SimpleNamespace(
        item_id=42,
        ebay_id="abc",
        title="Old title",
        price=100.0,
        currency="GBP",
        last_updated=None,
    )
    repository.items_by_ebay_id["abc"] = existing
    repository.query_links[(query.query_id, existing.item_id)] = SimpleNamespace(
        auction_ending_notification_sent=False
    )

    result = SearchItemProcessor(
        item_repository=repository,
        event_repository=repository,
        observation_repository=repository,
        notification_service=FakeNotifications(),
    ).process(
        [{"ebay_id": "abc", "title": "New title", "price": 75.0}], query, notify=False
    )

    assert result.updated_items == [existing]
    assert result.price_drops == [
        {"item": existing, "old_price": 100.0, "new_price": 75.0}
    ]
    assert [event.event_type for event in result.domain_events] == [
        ITEM_UPDATED,
        PRICE_DROPPED,
    ]
    assert result.domain_events[0].payload["changes"]["title"] == {
        "old": "Old title",
        "new": "New title",
    }
    assert repository.observations[0]["item_id"] == existing.item_id


def test_processor_records_auction_ending_event(monkeypatch: Any) -> None:
    monkeypatch.setattr(item_processor.db, "session", FakeSession())
    repository = FakeRepository()
    query = _query()
    existing = SimpleNamespace(item_id=7, ebay_id="auction-1", price=50.0)
    repository.items_by_ebay_id["auction-1"] = existing
    link = SimpleNamespace(auction_ending_notification_sent=False)
    repository.query_links[(query.query_id, existing.item_id)] = link

    end_time = datetime.now(timezone.utc) + timedelta(hours=2)
    result = SearchItemProcessor(
        item_repository=repository,
        event_repository=repository,
        observation_repository=repository,
        notification_service=FakeNotifications(),
    ).process(
        [
            {
                "ebay_id": "auction-1",
                "title": "Auction",
                "price": 50.0,
                "end_time": end_time,
            }
        ],
        query,
        notify=False,
    )

    assert result.ending_auctions == [existing]
    assert link.auction_ending_notification_sent is True
    assert [event.event_type for event in result.domain_events] == [AUCTION_ENDING_SOON]
    assert result.domain_events[0].payload["end_time"] == end_time


def test_legacy_process_items_return_shape_is_preserved(monkeypatch: Any) -> None:
    class StubProcessor:
        def process(self, **kwargs: Any) -> SearchProcessingResult:
            return SearchProcessingResult(new_items=["new"], updated_items=["updated"])

    monkeypatch.setattr(item_processor, "SearchItemProcessor", StubProcessor)

    assert process_items([], _query()) == (["new"], ["updated"])


def _query(search_run_id: str | None = None) -> Any:
    query = SimpleNamespace(
        query_id="search-1",
        user_id=100,
        keyword=SimpleNamespace(keyword_id=200, keyword_text="pokemon"),
    )
    if search_run_id is not None:
        query.search_run_id = search_run_id
    return query
