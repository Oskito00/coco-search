from datetime import datetime
from typing import Any, Optional

from app.repositories._optional import OptionalModelRepository


class SearchRunRepository(OptionalModelRepository):
    """Persistence operations for search execution runs.

    This repository expects a SearchRun model from the schema-worker branch
    before its write methods can persist records.
    """

    model_name = "SearchRun"

    def create(
        self,
        query_id: Optional[Any] = None,
        run_type: str = "scheduled",
        status: str = "started",
        source: Optional[str] = None,
        started_at: Optional[datetime] = None,
        metadata_json: Optional[dict[str, Any]] = None,
        search_id: Optional[Any] = None,
        **extra: Any,
    ) -> Any:
        """Create one search run record."""
        normalized_query_id = self._query_id(query_id=query_id, search_id=search_id)
        values = self.values(
            query_id=normalized_query_id,
            run_type=run_type,
            status=status,
            source=source,
            started_at=started_at or self.now(),
            metadata_json=metadata_json or {},
            **extra,
        )
        return self.add(values)

    def mark_finished(
        self,
        run: Any,
        status: str,
        finished_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        **stats: Any,
    ) -> Any:
        """Mark a search run as finished."""
        values = self.values(
            status=status,
            finished_at=finished_at or self.now(),
            error_message=error_message,
            **stats,
        )
        self.update(run, values)
        self.session.flush()
        return run

    def list_recent(self, query_id: Any, limit: int = 20) -> list[Any]:
        """Return recent runs for one saved search."""
        return (
            self.model.query.filter_by(query_id=query_id)
            .order_by(self.model.started_at.desc())
            .limit(limit)
            .all()
        )

    def _query_id(self, query_id: Optional[Any], search_id: Optional[Any]) -> Any:
        if query_id is not None:
            return query_id
        if search_id is not None:
            return search_id
        raise ValueError("query_id is required")
