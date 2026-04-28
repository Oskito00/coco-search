from __future__ import annotations

from typing import Any

from app.notifications.delivery import NotificationRenderer, NotificationSender
from app.notifications.events import NOTIFICATION_TYPES, SearchEventSelector
from app.notifications.preferences import NotificationPreferencePolicy
from app.notifications.records import NotificationRecordCreator
from app.notifications.relevance import NotificationRelevanceFilter, RelevanceService


class UserNotificationRepository:
    """Load users for notification delivery."""

    def get(self, user_id: int) -> Any:
        """Return a user by id, or None when unavailable."""
        from app.models import User

        return User.query.get(user_id)


class EventNotificationService:
    """Consume search events and dispatch user notifications."""

    def __init__(
        self,
        user_repository: Any | None = None,
        relevance_service: RelevanceService | None = None,
        notification_repository: Any | None = None,
        selector: SearchEventSelector | None = None,
        preference_policy: NotificationPreferencePolicy | None = None,
        renderer: NotificationRenderer | None = None,
        sender: NotificationSender | None = None,
    ) -> None:
        self.users = user_repository or UserNotificationRepository()
        self.selector = selector or SearchEventSelector()
        self.preferences = preference_policy or NotificationPreferencePolicy()
        self.relevance = NotificationRelevanceFilter(relevance_service)
        self.records = NotificationRecordCreator(notification_repository)
        self.renderer = renderer or NotificationRenderer()
        self.sender = sender or NotificationSender()

    def notify_search_events(self, query: Any, result: Any) -> dict[str, int]:
        """Notify a user about search processing result events."""
        counts = self._empty_counts()

        for event in self.selector.select(query, result):
            user = self.users.get(event.user_id)
            if user is None or not self.preferences.allows(
                user, event.notification_type
            ):
                continue

            payloads = self.relevance.relevant_payloads(event)
            if not payloads:
                continue

            rendered = self.renderer.render(event, payloads)
            self.records.create_records(user, event, payloads)
            self.sender.send(user, rendered)
            counts[event.notification_type] += len(payloads)

        return counts

    def _empty_counts(self) -> dict[str, int]:
        return {notification_type: 0 for notification_type in NOTIFICATION_TYPES}
