from datetime import datetime, timezone
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

    def __init__(self, session: Any | None = None) -> None:
        self.session = session or db.session

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
        relevance_label = _label_to_bool(label)
        if relevance_label is None:
            return interaction

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
        return RelevanceInteraction(
            user_id=user_id,
            search_id=str(search_id),
            item_id=str(item_id),
            interaction_type=interaction_type,
            label=label,
            source=source,
            persisted=True,
        )


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
