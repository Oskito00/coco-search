"""Item-observation persistence collaborator used by the search item processor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.searches.processing.serialization import serialize_for_persistence


@dataclass(frozen=True)
class ObservationContext:
    """Inputs needed to persist one item observation row."""

    item: Any
    item_data: dict[str, Any]
    query: Any
    observed_at: datetime
    is_new_item: bool
    hard_filter_passed: bool = True


def build_observation_payload(context: ObservationContext) -> dict[str, Any]:
    """Return the persistence-ready dict for a single observation."""
    item_data = context.item_data
    return {
        "item_id": getattr(context.item, "item_id", None),
        "query_id": getattr(context.query, "query_id", None),
        "search_run_id": _search_run_id(context.query, item_data),
        "observed_at": context.observed_at,
        "price": item_data.get("price"),
        "currency": item_data.get("currency"),
        "current_bid": item_data.get("current_bid"),
        "condition": item_data.get("condition"),
        "buying_options": item_data.get("buying_options"),
        "raw_item_snapshot": serialize_for_persistence(item_data),
        "is_new_item": context.is_new_item,
        "hard_filter_passed": context.hard_filter_passed,
    }


class ObservationRecorder:
    """Persist an :class:`ItemObservation` through a repository's ``create()`` API."""

    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def record(self, context: ObservationContext) -> Any:
        """Write a single observation derived from *context*."""
        return self.repository.create(**build_observation_payload(context))


class NoopObservationRecorder:
    """Recorder that intentionally drops observations (useful in tests / dry-runs)."""

    def record(self, context: ObservationContext) -> None:
        return None


def _search_run_id(query: Any, item_data: dict[str, Any]) -> Any:
    return (
        item_data.get("search_run_id")
        or getattr(query, "search_run_id", None)
        or getattr(query, "current_search_run_id", None)
    )
