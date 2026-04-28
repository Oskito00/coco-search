"""Repository base class for schema-worker tables that may not exist yet."""

from datetime import datetime, timezone
from typing import Any, Optional, Type

from app.repositories._models import (
    compact_values,
    create_model,
    default_session,
    optional_model,
    require_model,
    update_model,
)


class OptionalModelRepository:
    """Small repository wrapper around a model that may arrive in another branch."""

    model_name = ""

    def __init__(
        self, session: Optional[Any] = None, model: Optional[Type[Any]] = None
    ):
        self.session = session or default_session()
        self._model = model or optional_model(self.model_name)

    @property
    def model(self) -> Type[Any]:
        """Return the configured model or raise a clear dependency error."""
        return require_model(self._model, self.model_name)

    def get(self, record_id: Any) -> Any:
        """Return one record by primary key."""
        return self.session.get(self.model, record_id)

    def add(self, values: dict[str, Any]) -> Any:
        """Create and add one model instance."""
        record = create_model(self.model, values)
        self.session.add(record)
        self.session.flush()
        return record

    def update(self, record: Any, values: dict[str, Any]) -> bool:
        """Update one record with mapped values."""
        return update_model(record, values)

    def now(self) -> datetime:
        """Return a timezone-aware timestamp for repository defaults."""
        return datetime.now(timezone.utc)

    def values(self, **values: Any) -> dict[str, Any]:
        """Return non-null values for model construction."""
        return compact_values(values)
