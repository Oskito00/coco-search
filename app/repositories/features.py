from typing import Any, Optional

from app.repositories._optional import OptionalModelRepository


class ItemFeatureSnapshotRepository(OptionalModelRepository):
    """Persistence operations for item feature snapshots.

    This repository expects an ItemFeatureSnapshot model from the schema-worker
    branch before its write methods can persist records.
    """

    model_name = "ItemFeatureSnapshot"

    def create(
        self,
        item_id: int,
        query_id: Optional[Any] = None,
        features: Optional[dict[str, Any]] = None,
        search_run_id: Optional[int] = None,
        feature_version: str = "v1",
        model_version: Optional[str] = None,
        search_id: Optional[Any] = None,
        **extra: Any,
    ) -> Any:
        """Create one item feature snapshot."""
        normalized_query_id = self._query_id(query_id=query_id, search_id=search_id)
        values = self.values(
            item_id=item_id,
            query_id=normalized_query_id,
            search_run_id=search_run_id,
            feature_version=feature_version,
            model_version=model_version,
            features=features or {},
            created_at=extra.pop("created_at", self.now()),
            **extra,
        )
        return self.add(values)

    def latest_for_item(self, item_id: int) -> Any:
        """Return the latest feature snapshot for an item."""
        return (
            self.model.query.filter_by(item_id=item_id)
            .order_by(self.model.created_at.desc())
            .first()
        )

    def latest_for_search_item(self, search_id: Any, item_id: int) -> Any:
        """Return the latest feature snapshot for a saved-search item pair."""
        return self.latest_for_query_item(query_id=search_id, item_id=item_id)

    def _query_id(self, query_id: Optional[Any], search_id: Optional[Any]) -> Any:
        if query_id is not None:
            return query_id
        if search_id is not None:
            return search_id
        raise ValueError("query_id is required")

    def latest_for_query_item(self, query_id: Any, item_id: int) -> Any:
        """Return the latest feature snapshot for a saved-search item pair."""
        return (
            self.model.query.filter_by(query_id=query_id, item_id=item_id)
            .order_by(self.model.created_at.desc())
            .first()
        )
