from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.notifications.events import NotificationEvent, item_from_payload


@dataclass(frozen=True)
class NotificationSearchContext:
    """Search context passed to relevance services."""

    id: Any
    user_id: int
    keyword_id: Any
    keywords: str
    marketplace: str | None
    filters: dict[str, Any]
    schedule: dict[str, Any]


@dataclass(frozen=True)
class NotificationRelevanceDecision:
    """Fallback relevance decision used when no service is injected."""

    score: float
    should_notify: bool
    reasons: tuple[str, ...] = ()


class RelevanceService(Protocol):
    """Interface expected from learned or rules-based relevance services."""

    def should_notify(
        self,
        user_id: int,
        saved_search: NotificationSearchContext,
        item: Any,
    ) -> Any:
        """Return a relevance decision for a notification candidate."""


class AllowAllRelevanceService:
    """Preserve legacy behavior when no relevance service is configured."""

    def should_notify(
        self,
        user_id: int,
        saved_search: NotificationSearchContext,
        item: Any,
    ) -> NotificationRelevanceDecision:
        """Allow every item through the notification pipeline."""
        return NotificationRelevanceDecision(
            score=1.0,
            should_notify=True,
            reasons=("legacy_allow_all",),
        )


class NotificationRelevanceFilter:
    """Apply relevance decisions to event payloads."""

    def __init__(self, relevance_service: RelevanceService | None = None) -> None:
        self.relevance_service = relevance_service or AllowAllRelevanceService()

    def relevant_payloads(self, event: NotificationEvent) -> list[Any]:
        """Return payloads that should still notify after relevance checks."""
        search = search_context_from_query(event.query)
        return [
            payload
            for payload in event.payloads
            if self._should_notify(event.user_id, search, item_from_payload(payload))
        ]

    def _should_notify(
        self,
        user_id: int,
        search: NotificationSearchContext,
        item: Any,
    ) -> bool:
        if item is None:
            return False

        decision = self.relevance_service.should_notify(user_id, search, item)
        return bool(getattr(decision, "should_notify", decision))


def search_context_from_query(query: Any) -> NotificationSearchContext:
    """Build a relevance-compatible search context from the legacy query model."""
    return NotificationSearchContext(
        id=getattr(query, "query_id", getattr(query, "id", None)),
        user_id=getattr(query, "user_id"),
        keyword_id=getattr(query, "keyword_id", None),
        keywords=getattr(getattr(query, "keyword", None), "keyword_text", ""),
        marketplace=getattr(query, "marketplace", None),
        filters={
            "min_price": getattr(query, "min_price", None),
            "max_price": getattr(query, "max_price", None),
            "item_location": getattr(query, "item_location", None),
            "condition": getattr(query, "condition", None),
            "buying_options": getattr(query, "buying_options", None),
            "required_keywords": getattr(query, "required_keywords", None),
            "excluded_keywords": getattr(query, "excluded_keywords", None),
        },
        schedule={
            "check_interval": getattr(query, "check_interval", None),
            "first_run": getattr(query, "first_run", None),
            "last_full_run": getattr(query, "last_full_run", None),
            "next_full_run": getattr(query, "next_full_run", None),
            "last_recent_run": getattr(query, "last_recent_run", None),
        },
    )
