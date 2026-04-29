from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

from app.notifications.channels import DeliveryResult
from app.notifications.events import NotificationEvent
from app.notifications.service import EventNotificationService


@dataclass
class ItemStub:
    item_id: int
    title: str


class UserRepositoryStub:
    def __init__(self, user: Any | None) -> None:
        self.user = user

    def get(self, user_id: int) -> Any | None:
        return self.user


class RelevanceServiceStub:
    def __init__(self, allowed_item_ids: set[int]) -> None:
        self.allowed_item_ids = allowed_item_ids
        self.calls: list[tuple[int, Any, Any]] = []

    def should_notify(self, user_id: int, saved_search: Any, item: Any) -> Any:
        self.calls.append((user_id, saved_search, item))
        return SimpleNamespace(should_notify=item.item_id in self.allowed_item_ids)


class NotificationRepositoryStub:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self.sent: list[dict[str, Any]] = []
        self.failed: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> dict[str, Any]:
        self.records.append(kwargs)
        return kwargs

    def mark_sent(self, record: dict[str, Any]) -> None:
        self.sent.append(record)

    def mark_failed(self, record: dict[str, Any]) -> None:
        self.failed.append(record)


@dataclass
class DispatcherStub:
    """Captures dispatch calls and reports a configurable delivery outcome."""

    delivered: bool = True
    calls: list[tuple[Any, NotificationEvent, list[Any]]] = field(default_factory=list)

    def dispatch(
        self, user: Any, event: NotificationEvent, payloads: list[Any]
    ) -> list[DeliveryResult]:
        self.calls.append((user, event, list(payloads)))
        return [
            DeliveryResult(channel="telegram", delivered=self.delivered),
            DeliveryResult(channel="email", delivered=self.delivered),
        ]


def test_notify_search_events_filters_by_relevance_and_records_notifications() -> None:
    user = _user(preferences={"new_items": True})
    query = _query(user_id=user.id)
    first_item = ItemStub(item_id=1, title="wanted item")
    second_item = ItemStub(item_id=2, title="ignored item")
    result = SimpleNamespace(
        new_items=[first_item, second_item],
        price_drops=[],
        ending_auctions=[],
    )
    relevance = RelevanceServiceStub(allowed_item_ids={1})
    records = NotificationRepositoryStub()
    dispatcher = DispatcherStub()

    counts = EventNotificationService(
        user_repository=UserRepositoryStub(user),
        relevance_service=relevance,
        notification_repository=records,
        dispatcher=dispatcher,
    ).notify_search_events(query, result)

    assert counts == {"new_items": 1, "price_drops": 0, "auction_alerts": 0}
    assert len(relevance.calls) == 2
    assert relevance.calls[0][1].keywords == "sony camera"
    assert dispatcher.calls[0][1].notification_type == "new_items"
    assert dispatcher.calls[0][2] == [first_item]
    assert records.records == [
        {
            "query_id": query.query_id,
            "payload": {
                "user_id": user.id,
                "notification_type": "new_items",
                "query_text": "sony camera",
                "item_id": first_item.item_id,
                "metadata": {},
            },
            "channel": "telegram",
            "status": "pending",
        }
    ]
    assert records.sent == records.records
    assert records.failed == []


def test_notify_search_events_respects_disabled_preferences() -> None:
    user = _user(preferences={"new_items": False, "price_drops": True})
    query = _query(user_id=user.id)
    result = SimpleNamespace(
        new_items=[ItemStub(item_id=1, title="hidden item")],
        price_drops=[],
        ending_auctions=[],
    )
    dispatcher = DispatcherStub()

    counts = EventNotificationService(
        user_repository=UserRepositoryStub(user),
        dispatcher=dispatcher,
    ).notify_search_events(query, result)

    assert counts == {"new_items": 0, "price_drops": 0, "auction_alerts": 0}
    assert dispatcher.calls == []


def test_notify_search_events_preserves_legacy_event_buckets() -> None:
    user = _user(
        preferences={
            "new_items": True,
            "price_drops": True,
            "auction_alerts": True,
        }
    )
    query = _query(user_id=user.id)
    dropped_item = ItemStub(item_id=2, title="discounted item")
    auction_item = ItemStub(item_id=3, title="ending item")
    result = SimpleNamespace(
        new_items=[ItemStub(item_id=1, title="new item")],
        price_drops=[{"item": dropped_item, "old_price": 20, "new_price": 15}],
        ending_auctions=[auction_item],
    )
    dispatcher = DispatcherStub()

    counts = EventNotificationService(
        user_repository=UserRepositoryStub(user),
        dispatcher=dispatcher,
    ).notify_search_events(query, result)

    assert counts == {"new_items": 1, "price_drops": 1, "auction_alerts": 1}
    assert [call[1].notification_type for call in dispatcher.calls] == [
        "new_items",
        "price_drops",
        "auction_alerts",
    ]
    assert dispatcher.calls[1][2] == result.price_drops
    assert dispatcher.calls[2][2] == result.ending_auctions


def test_notify_search_events_marks_records_failed_when_delivery_fails() -> None:
    user = _user(preferences={"new_items": True})
    query = _query(user_id=user.id)
    item = ItemStub(item_id=1, title="undelivered item")
    result = SimpleNamespace(
        new_items=[item],
        price_drops=[],
        ending_auctions=[],
    )
    records = NotificationRepositoryStub()

    counts = EventNotificationService(
        user_repository=UserRepositoryStub(user),
        notification_repository=records,
        dispatcher=DispatcherStub(delivered=False),
    ).notify_search_events(query, result)

    assert counts == {"new_items": 1, "price_drops": 0, "auction_alerts": 0}
    assert records.sent == []
    assert records.failed == records.records


def _user(preferences: dict[str, bool]) -> Any:
    return SimpleNamespace(
        id=7,
        notification_preferences=preferences,
        telegram_notifications_enabled=True,
    )


def _query(user_id: int) -> Any:
    return SimpleNamespace(
        query_id="search-1",
        user_id=user_id,
        keyword_id=11,
        keyword=SimpleNamespace(keyword_text="sony camera"),
        marketplace="EBAY_GB",
        min_price=None,
        max_price=None,
        item_location="GB",
        condition=None,
        buying_options=None,
        required_keywords=None,
        excluded_keywords=None,
        check_interval=10,
        first_run=False,
        last_full_run=None,
        next_full_run=None,
        last_recent_run=None,
    )
