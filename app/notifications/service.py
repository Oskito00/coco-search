"""Top-level notification orchestrator: select events, filter, dispatch, record.

The service is intentionally thin: it composes single-purpose collaborators
(``SearchEventSelector``, ``NotificationPreferencePolicy``,
``NotificationRelevanceFilter``, ``NotificationDispatcher``,
``NotificationRecordCreator``) so that adding a new channel or swapping a
relevance scorer never requires changes here.
"""

from __future__ import annotations

from typing import Any

from app.notifications.dispatch import NotificationDispatcher
from app.notifications.events import NOTIFICATION_TYPES, SearchEventSelector
from app.notifications.preferences import NotificationPreferencePolicy
from app.notifications.records import NotificationRecordCreator
from app.notifications.relevance import NotificationRelevanceFilter, RelevanceService


class UserNotificationRepository:
    """Load users for notification delivery."""

    def get(self, user_id: int) -> Any:
        from app.models import User

        return User.query.get(user_id)


class EventNotificationService:
    """Consume search events and dispatch notifications across channels."""

    def __init__(
        self,
        user_repository: Any | None = None,
        relevance_service: RelevanceService | None = None,
        notification_repository: Any | None = None,
        selector: SearchEventSelector | None = None,
        preference_policy: NotificationPreferencePolicy | None = None,
        dispatcher: NotificationDispatcher | None = None,
    ) -> None:
        self.users = user_repository or UserNotificationRepository()
        self.selector = selector or SearchEventSelector()
        self.preferences = preference_policy or NotificationPreferencePolicy()
        self.relevance = NotificationRelevanceFilter(relevance_service)
        self.records = NotificationRecordCreator(notification_repository)
        self.dispatcher = dispatcher or NotificationDispatcher()

    def notify_search_events(self, query: Any, result: Any) -> dict[str, int]:
        """Notify the search owner about every populated event bucket."""
        counts = self._empty_counts()
        for event in self.selector.select(query, result):
            counts[event.notification_type] += self._handle_event(event)
        return counts

    def _handle_event(self, event: Any) -> int:
        user = self.users.get(event.user_id)
        if user is None or not self.preferences.allows(user, event.notification_type):
            return 0

        payloads = self.relevance.relevant_payloads(event)
        if not payloads:
            return 0

        records = self.records.create_records(user, event, payloads)
        delivered = self._dispatch(user, event, payloads)
        self._mark_records(records, delivered)
        return len(payloads)

    def _dispatch(self, user: Any, event: Any, payloads: list[Any]) -> bool:
        results = self.dispatcher.dispatch(user, event, payloads)
        return any(result.delivered for result in results)

    def _mark_records(self, records: list[Any], delivered: bool) -> None:
        if delivered:
            self.records.mark_sent(records)
        else:
            self.records.mark_failed(records)

    @staticmethod
    def _empty_counts() -> dict[str, int]:
        return {notification_type: 0 for notification_type in NOTIFICATION_TYPES}
