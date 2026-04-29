"""Domain-event persistence collaborator used by the search item processor."""

from __future__ import annotations

from typing import Any

from app.searches.events import DomainEvent
from app.searches.processing.serialization import serialize_for_persistence

EVENT_SOURCE = "search_item_processor"


class EventRecorder:
    """Persist a :class:`DomainEvent` through a repository's ``create()`` API."""

    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def record(self, event: DomainEvent) -> Any:
        """Write a single event to the repository."""
        return self.repository.create(
            event_type=event.event_type,
            aggregate_type="item",
            aggregate_id=event.item_id or event.ebay_id,
            user_id=event.user_id,
            query_id=event.search_id,
            item_id=event.item_id,
            payload=serialize_for_persistence(event.payload),
            status="pending",
            source=EVENT_SOURCE,
            occurred_at=event.occurred_at,
        )


class NoopEventRecorder:
    """Recorder that intentionally drops events (useful in tests / dry-runs)."""

    def record(self, event: DomainEvent) -> None:
        return None
