from datetime import datetime, timezone
from importlib import import_module
from typing import Any, Protocol

from app.extensions import db
from app.models import ItemRelevanceFeedback, UserQuery
from app.relevance.domain import RelevanceInteraction


class RelevanceRepository(Protocol):
    """Storage contract used by RelevanceService."""

    def get_feedback(
        self,
        user_id: int,
        saved_search: Any,
        item: Any,
    ) -> Any | None:
        """Return stored user feedback for this search item, if available."""

    def record_interaction(
        self,
        user_id: int,
        search_id: str,
        item_id: str,
        interaction_type: str,
        label: str | None = None,
        source: str | None = None,
    ) -> object:
        """Record a user interaction for later model training."""


class SqlAlchemyRelevanceRepository:
    """Default adapter over the legacy relevance feedback table."""

    def __init__(
        self,
        session: Any | None = None,
        interaction_repository: Any | None = None,
    ) -> None:
        self.session = session or db.session
        self.interactions = interaction_repository

    def get_feedback(
        self,
        user_id: int,
        saved_search: Any,
        item: Any,
    ) -> ItemRelevanceFeedback | None:
        item_id = _object_id(item, "item_id", "id")
        keyword_id = _keyword_id(saved_search)
        if item_id is None or keyword_id is None:
            return None
        return ItemRelevanceFeedback.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            keyword_id=keyword_id,
        ).one_or_none()

    def record_interaction(
        self,
        user_id: int,
        search_id: str,
        item_id: str,
        interaction_type: str,
        label: str | None = None,
        source: str | None = None,
    ) -> object:
        interaction = RelevanceInteraction(
            user_id=user_id,
            search_id=str(search_id),
            item_id=str(item_id),
            interaction_type=interaction_type,
            label=label,
            source=source,
            persisted=False,
        )
        if self._interaction_schema_available():
            persisted = self._record_user_item_interaction(
                user_id=user_id,
                search_id=search_id,
                item_id=item_id,
                interaction_type=interaction_type,
                label=label,
                source=source,
            )
            if persisted is not None:
                return _persisted_interaction(interaction)

        relevance_label = _label_to_bool(label)
        if relevance_label is None:
            return interaction

        return self._record_legacy_feedback(
            interaction=interaction,
            user_id=user_id,
            search_id=search_id,
            item_id=item_id,
            relevance_label=relevance_label,
        )

    def _interaction_schema_available(self) -> bool:
        if self.interactions is not None:
            return True
        if _optional_model("UserItemInteraction") is None:
            return False
        self.interactions = _optional_interaction_repository(self.session)
        return self.interactions is not None

    def _record_user_item_interaction(
        self,
        user_id: int,
        search_id: str,
        item_id: str,
        interaction_type: str,
        label: str | None,
        source: str | None,
    ) -> object | None:
        if self.interactions is None:
            return None

        metadata_json = _interaction_metadata(search_id)
        for payload in _interaction_payloads(
            user_id=user_id,
            search_id=search_id,
            item_id=item_id,
            interaction_type=interaction_type,
            label=label,
            source=source,
            metadata_json=metadata_json,
        ):
            persisted = _call_record_interaction(self.interactions, payload)
            if persisted is not None:
                return persisted
        return None

    def _record_legacy_feedback(
        self,
        interaction: RelevanceInteraction,
        user_id: int,
        search_id: str,
        item_id: str,
        relevance_label: bool,
    ) -> RelevanceInteraction:
        query = UserQuery.query.filter_by(query_id=search_id).one_or_none()
        if query is None:
            return interaction

        feedback = ItemRelevanceFeedback.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            keyword_id=query.keyword_id,
        ).one_or_none()
        if feedback is None:
            feedback = ItemRelevanceFeedback(
                user_id=user_id,
                item_id=item_id,
                keyword_id=query.keyword_id,
                required_keywords=query.required_keywords,
                excluded_keywords=query.excluded_keywords,
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(feedback)

        feedback.is_relevant = relevance_label
        feedback.required_keywords = query.required_keywords
        feedback.excluded_keywords = query.excluded_keywords
        self.session.flush()
        return _persisted_interaction(interaction)


def _persisted_interaction(interaction: RelevanceInteraction) -> RelevanceInteraction:
    return RelevanceInteraction(
        user_id=interaction.user_id,
        search_id=interaction.search_id,
        item_id=interaction.item_id,
        interaction_type=interaction.interaction_type,
        label=interaction.label,
        source=interaction.source,
        persisted=True,
    )


def _optional_model(name: str) -> type[Any] | None:
    try:
        models = import_module("app.models")
    except ImportError:
        return None
    return getattr(models, name, None)


def _optional_interaction_repository(session: Any) -> Any | None:
    try:
        repositories = import_module("app.repositories")
    except ImportError:
        return None
    repository_class = getattr(repositories, "InteractionRepository", None)
    if repository_class is None:
        return None
    try:
        return repository_class(session=session)
    except TypeError:
        return repository_class()


def _interaction_metadata(search_id: str) -> dict[str, str]:
    return {"search_id": str(search_id)}


def _interaction_payloads(
    user_id: int,
    search_id: str,
    item_id: str,
    interaction_type: str,
    label: str | None,
    source: str | None,
    metadata_json: dict[str, str],
) -> tuple[dict[str, Any], ...]:
    base_payload = {
        "user_id": user_id,
        "item_id": item_id,
        "interaction_type": interaction_type,
        "label": label,
        "source": source,
    }
    with_query_id = {
        **base_payload,
        "query_id": search_id,
        "metadata_json": metadata_json,
    }
    with_search_id = {
        **base_payload,
        "search_id": search_id,
        "metadata_json": metadata_json,
    }
    return (
        with_query_id,
        with_search_id,
        {key: value for key, value in with_query_id.items() if key != "metadata_json"},
        {key: value for key, value in with_search_id.items() if key != "metadata_json"},
    )


def _call_record_interaction(repository: Any, payload: dict[str, Any]) -> object | None:
    added_record = _call_add_interaction_record(repository, payload)
    if added_record is not None:
        return added_record

    recorder = getattr(repository, "record_interaction", None)
    if recorder is None:
        recorder = getattr(repository, "record", None)
    if recorder is None:
        return None
    try:
        return recorder(**payload)
    except TypeError:
        return None


def _call_add_interaction_record(
    repository: Any,
    payload: dict[str, Any],
) -> object | None:
    if "query_id" not in payload:
        return None

    values = getattr(repository, "values", None)
    add = getattr(repository, "add", None)
    if values is None or add is None:
        return None

    try:
        return add(values(**payload))
    except TypeError:
        return None


def _object_id(source: Any, *names: str) -> Any:
    for name in names:
        value = (
            source.get(name)
            if isinstance(source, dict)
            else getattr(source, name, None)
        )
        if value is not None:
            return value
    return None


def _keyword_id(saved_search: Any) -> Any:
    keyword_id = _object_id(saved_search, "keyword_id")
    if keyword_id is not None:
        return keyword_id
    keyword = (
        saved_search.get("keyword")
        if isinstance(saved_search, dict)
        else getattr(
            saved_search,
            "keyword",
            None,
        )
    )
    return _object_id(keyword, "keyword_id", "id") if keyword is not None else None


def _label_to_bool(label: str | None) -> bool | None:
    if label is None:
        return None
    normalized = label.strip().lower()
    if normalized in {"relevant", "positive", "true", "yes", "1"}:
        return True
    if normalized in {"irrelevant", "negative", "false", "no", "0"}:
        return False
    return None
