from typing import Any, Optional, Type

from app.extensions import db
from app.models import ItemRelevanceFeedback, UserQuery
from app.repositories._optional import OptionalModelRepository


class FeedbackRepository:
    """Persistence operations for relevance feedback using the legacy table."""

    def __init__(self, session: Optional[Any] = None):
        self.session = session or db.session

    def get(
        self, user_id: int, item_id: int, keyword_id: int
    ) -> Optional[ItemRelevanceFeedback]:
        """Return one relevance feedback record."""
        return ItemRelevanceFeedback.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            keyword_id=keyword_id,
        ).one_or_none()

    def record(
        self,
        user_id: int,
        item_id: int,
        keyword_id: int,
        is_relevant: Optional[bool],
        **scores: Any,
    ) -> ItemRelevanceFeedback:
        """Create or update legacy relevance feedback."""
        feedback = self.get(user_id, item_id, keyword_id)
        if feedback is None:
            feedback = ItemRelevanceFeedback(
                user_id=user_id,
                item_id=item_id,
                keyword_id=keyword_id,
            )
            self.session.add(feedback)

        feedback.is_relevant = is_relevant
        self._update_scores(feedback, scores)
        self.session.flush()
        return feedback

    def _update_scores(
        self, feedback: ItemRelevanceFeedback, scores: dict[str, Any]
    ) -> None:
        for key in ("required_keywords", "excluded_keywords"):
            if key in scores:
                setattr(feedback, key, scores[key])

        for key in ("simple_hybrid_levenshtein_confidence", "cosine_similarity"):
            if key in scores:
                setattr(feedback, key, scores[key])


class InteractionRepository(OptionalModelRepository):
    """Persistence operations for user item interactions.

    The future schema is expected to expose a UserItemInteraction model. Until
    then, relevance-style interactions are stored in ItemRelevanceFeedback.
    """

    model_name = "UserItemInteraction"

    def __init__(
        self,
        session: Optional[Any] = None,
        model: Optional[Type[Any]] = None,
        feedback_repository: Optional[FeedbackRepository] = None,
    ):
        super().__init__(session=session, model=model)
        self.feedback = feedback_repository or FeedbackRepository(self.session)

    def record_interaction(
        self,
        user_id: int,
        item_id: int,
        interaction_type: str,
        query_id: Optional[Any] = None,
        label: Optional[Any] = None,
        source: Optional[str] = None,
        metadata_json: Optional[dict[str, Any]] = None,
        search_id: Optional[Any] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Record a user interaction, falling back to legacy feedback when possible."""
        normalized_query_id = self._query_id(query_id=query_id, search_id=search_id)
        normalized_metadata = (
            metadata_json if metadata_json is not None else metadata or {}
        )
        if self._model is not None:
            return self.add(
                self.values(
                    user_id=user_id,
                    query_id=normalized_query_id,
                    item_id=item_id,
                    interaction_type=interaction_type,
                    label=label,
                    source=source,
                    metadata_json=normalized_metadata,
                )
            )

        query = self._get_query(normalized_query_id)
        relevance = self._relevance_label(interaction_type, label)
        return self.feedback.record(
            user_id=user_id,
            item_id=item_id,
            keyword_id=query.keyword_id,
            is_relevant=relevance,
        )

    def _get_query(self, query_id: Any) -> UserQuery:
        query = self.session.get(UserQuery, query_id)
        if query is None:
            raise ValueError(f"Saved search {query_id} was not found")
        return query

    def _query_id(self, query_id: Optional[Any], search_id: Optional[Any]) -> Any:
        if query_id is not None:
            return query_id
        if search_id is not None:
            return search_id
        raise ValueError("query_id is required")

    def _relevance_label(
        self, interaction_type: str, label: Optional[Any]
    ) -> Optional[bool]:
        if isinstance(label, bool):
            return label
        if isinstance(label, str):
            return self._string_label(label)
        return self._string_label(interaction_type)

    def _string_label(self, value: str) -> Optional[bool]:
        normalized = value.lower().strip()
        if normalized in {"relevant", "positive", "like", "liked"}:
            return True
        if normalized in {"irrelevant", "negative", "dislike", "dismissed", "hidden"}:
            return False
        return None
