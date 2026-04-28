from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

NEW_ITEMS = "new_items"
PRICE_DROPS = "price_drops"
AUCTION_ALERTS = "auction_alerts"

NOTIFICATION_TYPES = (NEW_ITEMS, PRICE_DROPS, AUCTION_ALERTS)


@dataclass(frozen=True)
class NotificationEvent:
    """Domain event consumed by the notification pipeline."""

    notification_type: str
    user_id: int
    search_id: Any
    query_text: str
    payloads: tuple[Any, ...]
    query: Any


class SearchEventSelector:
    """Convert search processing results into notification domain events."""

    def select(self, query: Any, result: Any) -> list[NotificationEvent]:
        """Return notification events for populated result buckets."""
        query_text = getattr(getattr(query, "keyword", None), "keyword_text", "")
        return [
            event
            for event in (
                self._event(query, result, NEW_ITEMS, "new_items", query_text),
                self._event(query, result, PRICE_DROPS, "price_drops", query_text),
                self._event(
                    query, result, AUCTION_ALERTS, "ending_auctions", query_text
                ),
            )
            if event is not None
        ]

    def _event(
        self,
        query: Any,
        result: Any,
        notification_type: str,
        result_attr: str,
        query_text: str,
    ) -> NotificationEvent | None:
        payloads = tuple(self._payloads(result, result_attr))
        if not payloads:
            return None

        return NotificationEvent(
            notification_type=notification_type,
            user_id=getattr(query, "user_id"),
            search_id=getattr(query, "query_id", getattr(query, "id", None)),
            query_text=query_text,
            payloads=payloads,
            query=query,
        )

    def _payloads(self, result: Any, result_attr: str) -> Iterable[Any]:
        return getattr(result, result_attr, None) or ()


def item_from_payload(payload: Any) -> Any:
    """Return the item object represented by an event payload."""
    if isinstance(payload, dict):
        return payload.get("item")
    return payload
