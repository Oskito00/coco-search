from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from app.notifications.delivery import NotificationSender, RenderedNotification
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

    def create_notification(self, **kwargs: Any) -> None:
        self.records.append(kwargs)


class SenderStub(NotificationSender):
    def __init__(self) -> None:
        self.sent: list[tuple[Any, RenderedNotification]] = []

    def send(self, user: Any, notification: RenderedNotification) -> bool:
        self.sent.append((user, notification))
        return True


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
    sender = SenderStub()

    counts = EventNotificationService(
        user_repository=UserRepositoryStub(user),
        relevance_service=relevance,
        notification_repository=records,
        sender=sender,
    ).notify_search_events(query, result)

    assert counts == {"new_items": 1, "price_drops": 0, "auction_alerts": 0}
    assert len(relevance.calls) == 2
    assert relevance.calls[0][1].keywords == "sony camera"
    assert sender.sent[0][1].notification_type == "new_items"
    assert sender.sent[0][1].payloads == [first_item]
    assert records.records == [
        {
            "user_id": user.id,
            "search_id": query.query_id,
            "item_id": first_item.item_id,
            "notification_type": "new_items",
            "metadata": {},
        }
    ]


def test_notify_search_events_respects_disabled_preferences() -> None:
    user = _user(preferences={"new_items": False, "price_drops": True})
    query = _query(user_id=user.id)
    result = SimpleNamespace(
        new_items=[ItemStub(item_id=1, title="hidden item")],
        price_drops=[],
        ending_auctions=[],
    )
    sender = SenderStub()

    counts = EventNotificationService(
        user_repository=UserRepositoryStub(user),
        sender=sender,
    ).notify_search_events(query, result)

    assert counts == {"new_items": 0, "price_drops": 0, "auction_alerts": 0}
    assert sender.sent == []


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
    sender = SenderStub()

    counts = EventNotificationService(
        user_repository=UserRepositoryStub(user),
        sender=sender,
    ).notify_search_events(query, result)

    assert counts == {"new_items": 1, "price_drops": 1, "auction_alerts": 1}
    assert [sent[1].notification_type for sent in sender.sent] == [
        "new_items",
        "price_drops",
        "auction_alerts",
    ]
    assert sender.sent[1][1].payloads == result.price_drops
    assert sender.sent[2][1].payloads == result.ending_auctions


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
