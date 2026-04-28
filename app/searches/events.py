from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

ITEM_DISCOVERED = "item.discovered"
ITEM_UPDATED = "item.updated"
PRICE_DROPPED = "item.price_dropped"
AUCTION_ENDING_SOON = "item.auction_ending_soon"


@dataclass(frozen=True)
class DomainEvent:
    """Domain event emitted while processing items for a saved search."""

    event_type: str
    user_id: Any
    search_id: Any
    item_id: Any
    ebay_id: str | None
    occurred_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchProcessingResult:
    new_items: list[Any] = field(default_factory=list)
    updated_items: list[Any] = field(default_factory=list)
    price_drops: list[dict[str, Any]] = field(default_factory=list)
    ending_auctions: list[Any] = field(default_factory=list)
    domain_events: list[DomainEvent] = field(default_factory=list)


def build_item_discovered_event(
    query: Any, item: Any, occurred_at: datetime
) -> DomainEvent:
    """Create an event for an item newly associated with a search."""
    return _item_event(ITEM_DISCOVERED, query, item, occurred_at)


def build_item_updated_event(
    query: Any,
    item: Any,
    occurred_at: datetime,
    changes: dict[str, dict[str, Any]],
) -> DomainEvent:
    """Create an event for changed item attributes."""
    return _item_event(ITEM_UPDATED, query, item, occurred_at, {"changes": changes})


def build_price_dropped_event(
    query: Any,
    item: Any,
    occurred_at: datetime,
    old_price: float,
    new_price: float,
) -> DomainEvent:
    """Create an event for a lower observed item price."""
    return _item_event(
        PRICE_DROPPED,
        query,
        item,
        occurred_at,
        {"old_price": old_price, "new_price": new_price},
    )


def build_auction_ending_soon_event(
    query: Any,
    item: Any,
    occurred_at: datetime,
    end_time: datetime,
) -> DomainEvent:
    """Create an event for an auction ending inside the alert window."""
    return _item_event(
        AUCTION_ENDING_SOON,
        query,
        item,
        occurred_at,
        {"end_time": end_time},
    )


def _item_event(
    event_type: str,
    query: Any,
    item: Any,
    occurred_at: datetime,
    payload: dict[str, Any] | None = None,
) -> DomainEvent:
    return DomainEvent(
        event_type=event_type,
        user_id=getattr(query, "user_id", None),
        search_id=getattr(query, "query_id", None),
        item_id=getattr(item, "item_id", None),
        ebay_id=getattr(item, "ebay_id", None),
        occurred_at=occurred_at,
        payload=payload or {},
    )
