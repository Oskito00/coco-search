from datetime import datetime
from typing import Any, Optional

from app.repositories._optional import OptionalModelRepository


class ItemObservationRepository(OptionalModelRepository):
    """Persistence operations for item observation snapshots.

    This repository expects an ItemObservation model from the schema-worker
    branch before its write methods can persist records.
    """

    model_name = "ItemObservation"

    def create(
        self,
        item_id: int,
        query_id: Optional[Any] = None,
        observed_at: Optional[datetime] = None,
        search_run_id: Optional[int] = None,
        raw_item_snapshot: Optional[dict[str, Any]] = None,
        search_id: Optional[Any] = None,
        run_id: Optional[int] = None,
        payload: Optional[dict[str, Any]] = None,
        **extra: Any,
    ) -> Any:
        """Create one item observation snapshot."""
        normalized_query_id = self._query_id(query_id=query_id, search_id=search_id)
        normalized_run_id = self._search_run_id(
            search_run_id=search_run_id, run_id=run_id
        )
        snapshot = raw_item_snapshot if raw_item_snapshot is not None else payload
        values = self.values(
            item_id=item_id,
            query_id=normalized_query_id,
            search_run_id=normalized_run_id,
            observed_at=observed_at or self.now(),
            raw_item_snapshot=snapshot or {},
            **extra,
        )
        return self.add(values)

    def latest_for_item(self, item_id: int) -> Any:
        """Return the latest observation for an item."""
        return (
            self.model.query.filter_by(item_id=item_id)
            .order_by(self.model.observed_at.desc())
            .first()
        )

    def list_for_item(self, item_id: int, limit: int = 20) -> list[Any]:
        """Return recent observations for an item."""
        return (
            self.model.query.filter_by(item_id=item_id)
            .order_by(self.model.observed_at.desc())
            .limit(limit)
            .all()
        )

    def _query_id(self, query_id: Optional[Any], search_id: Optional[Any]) -> Any:
        if query_id is not None:
            return query_id
        if search_id is not None:
            return search_id
        raise ValueError("query_id is required")

    def _search_run_id(
        self,
        search_run_id: Optional[int],
        run_id: Optional[int],
    ) -> Optional[int]:
        if search_run_id is not None:
            return search_run_id
        return run_id

    def list_for_query(self, query_id: Any, limit: int = 50) -> list[Any]:
        """Return recent observations for a saved search."""
        return (
            self.model.query.filter_by(query_id=query_id)
            .order_by(self.model.observed_at.desc())
            .limit(limit)
            .all()
        )

    def list_for_run(self, search_run_id: int, limit: int = 100) -> list[Any]:
        """Return observations captured by one search run."""
        return (
            self.model.query.filter_by(search_run_id=search_run_id)
            .order_by(self.model.observed_at.desc())
            .limit(limit)
            .all()
        )
