from __future__ import annotations

from typing import Any

from app.notifications.events import NotificationEvent, item_from_payload


class NotificationRecordCreator:
    """Persist notification records through an injected repository."""

    def __init__(self, repository: Any | None = None) -> None:
        self.repository = repository

    def create_records(
        self,
        user: Any,
        event: NotificationEvent,
        payloads: list[Any],
    ) -> int:
        """Create records when a repository is available."""
        if self.repository is None:
            return 0

        created = 0
        for payload in payloads:
            if self._create_record(user, event, payload):
                created += 1
        return created

    def _create_record(self, user: Any, event: NotificationEvent, payload: Any) -> bool:
        item = item_from_payload(payload)
        item_id = getattr(item, "item_id", getattr(item, "id", None))
        metadata = self._metadata(payload)
        data = {
            "user_id": getattr(user, "id", event.user_id),
            "search_id": event.search_id,
            "item_id": item_id,
            "notification_type": event.notification_type,
            "metadata": metadata,
        }

        for method_name in ("create_notification", "create", "add"):
            method = getattr(self.repository, method_name, None)
            if method is not None:
                method(**data)
                return True
        return False

    def _metadata(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return {key: value for key, value in payload.items() if key != "item"}
        return {}
