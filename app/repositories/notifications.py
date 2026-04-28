from typing import Any, Optional

from app.repositories._optional import OptionalModelRepository


class NotificationRecordRepository(OptionalModelRepository):
    """Persistence operations for notification records.

    This repository expects a NotificationRecord model from the schema-worker
    branch before its write methods can persist records.
    """

    model_name = "NotificationRecord"

    def create(
        self,
        user_id: int,
        notification_type: str,
        channel: str,
        query_id: Optional[Any] = None,
        item_id: Optional[int] = None,
        domain_event_id: Optional[int] = None,
        status: str = "pending",
        recipient: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        search_id: Optional[Any] = None,
        metadata: Optional[dict[str, Any]] = None,
        **extra: Any,
    ) -> Any:
        """Create one notification record."""
        normalized_query_id = self._query_id(query_id=query_id, search_id=search_id)
        normalized_payload = payload if payload is not None else metadata
        values = self.values(
            user_id=user_id,
            query_id=normalized_query_id,
            item_id=item_id,
            domain_event_id=domain_event_id,
            notification_type=notification_type,
            channel=channel,
            status=status,
            recipient=recipient,
            payload=normalized_payload or {},
            created_at=extra.pop("created_at", self.now()),
            **extra,
        )
        return self.add(values)

    def mark_sent(self, record: Any, sent_at: Optional[Any] = None) -> Any:
        """Mark a notification as sent."""
        self.update(record, self.values(status="sent", sent_at=sent_at or self.now()))
        self.session.flush()
        return record

    def mark_failed(
        self,
        record: Any,
        error_message: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Any:
        """Mark a notification as failed."""
        values = self.values(
            status="failed",
            error_message=error_message or error,
        )
        self.update(record, values)
        self.session.flush()
        return record

    def list_for_user(self, user_id: int, limit: int = 50) -> list[Any]:
        """Return recent notification records for one user."""
        return (
            self.model.query.filter_by(user_id=user_id)
            .order_by(self.model.created_at.desc())
            .limit(limit)
            .all()
        )

    def _query_id(self, query_id: Optional[Any], search_id: Optional[Any]) -> Any:
        if query_id is not None:
            return query_id
        return search_id
