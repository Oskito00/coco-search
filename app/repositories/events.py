from typing import Any, Optional

from app.repositories._optional import OptionalModelRepository


class DomainEventRepository(OptionalModelRepository):
    """Persistence operations for domain events.

    This repository expects a DomainEvent model from the schema-worker branch
    before its write methods can persist records.
    """

    model_name = "DomainEvent"

    def create(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: Any,
        payload: Optional[dict[str, Any]] = None,
        status: str = "pending",
        **extra: Any,
    ) -> Any:
        """Create one domain event record."""
        values = self.values(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            status=status,
            payload=payload or {},
            occurred_at=extra.pop("occurred_at", self.now()),
            **extra,
        )
        return self.add(values)

    def mark_processed(self, event: Any, processed_at: Optional[Any] = None) -> Any:
        """Mark a domain event as processed."""
        self.update(event, self.values(processed_at=processed_at or self.now()))
        self.session.flush()
        return event

    def list_unprocessed(self, limit: int = 100) -> list[Any]:
        """Return unprocessed domain events in occurrence order."""
        return (
            self.model.query.filter_by(status="pending", processed_at=None)
            .order_by(self.model.occurred_at.asc())
            .limit(limit)
            .all()
        )
