from __future__ import annotations

from typing import Any

from app.notifications.events import NotificationEvent, item_from_payload


class NotificationRecordCreator:
    """Persist notification records through an injected repository."""

    def __init__(
        self, repository: Any | None = None, channel: str = "telegram"
    ) -> None:
        self.repository = repository
        self.channel = channel

    def create_records(
        self,
        user: Any,
        event: NotificationEvent,
        payloads: list[Any],
    ) -> list[Any]:
        """Create records when a repository is available."""
        repository = self.repository
        if repository is None or not hasattr(repository, "create"):
            return []

        records = []
        for payload in payloads:
            record = self._create_record(repository, user, event, payload)
            if record is not None:
                records.append(record)
        return records

    def mark_sent(self, records: list[Any]) -> None:
        """Mark created notification records as sent when supported."""
        self._mark_records("mark_sent", records)

    def mark_failed(self, records: list[Any]) -> None:
        """Mark created notification records as failed when supported."""
        self._mark_records("mark_failed", records)

    def _create_record(
        self,
        repository: Any,
        user: Any,
        event: NotificationEvent,
        payload: Any,
    ) -> Any:
        item = item_from_payload(payload)
        return repository.create(
            query_id=event.search_id,
            payload={
                "user_id": getattr(user, "id", event.user_id),
                "notification_type": event.notification_type,
                "query_text": event.query_text,
                "item_id": getattr(item, "item_id", getattr(item, "id", None)),
                "metadata": self._metadata(payload),
            },
            channel=self.channel,
            status="pending",
        )

    def _mark_records(self, method_name: str, records: list[Any]) -> None:
        if self.repository is None or not records:
            return

        method = getattr(self.repository, method_name, None)
        if method is None:
            return

        for record in records:
            method(record)

    def _metadata(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return {key: value for key, value in payload.items() if key != "item"}
        return {}
