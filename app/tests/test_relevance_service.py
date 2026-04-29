from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from app.relevance import RelevanceService
from app.relevance.domain import RelevanceInteraction
from app.relevance.repository import SqlAlchemyRelevanceRepository
from app.relevance.scoring import BaselineRelevanceScorer
import app.relevance.repository as relevance_repository


@dataclass(frozen=True)
class SearchFilters:
    min_price: float | None = None
    max_price: float | None = None
    item_location: str | None = "GB"
    condition: str | None = None
    buying_options: str = "FIXED_PRICE|AUCTION"
    required_keywords: str | None = None
    excluded_keywords: str | None = None


@dataclass(frozen=True)
class SavedSearch:
    id: str
    user_id: int
    keyword_id: int
    keywords: str
    marketplace: str
    is_active: bool
    filters: SearchFilters


@dataclass(frozen=True)
class Feedback:
    is_relevant: bool | None


class FakeRepository:
    def __init__(self, feedback: Feedback | None = None) -> None:
        self.feedback = feedback
        self.recorded_interactions: list[dict[str, Any]] = []

    def get_feedback(
        self,
        user_id: int,
        saved_search: SavedSearch,
        item: dict[str, Any],
    ) -> Feedback | None:
        return self.feedback

    def record_interaction(
        self,
        user_id: int,
        search_id: str,
        item_id: str,
        interaction_type: str,
        label: str | None = None,
        source: str | None = None,
    ) -> object:
        interaction = {
            "user_id": user_id,
            "search_id": search_id,
            "item_id": item_id,
            "interaction_type": interaction_type,
            "label": label,
            "source": source,
        }
        self.recorded_interactions.append(interaction)
        return interaction


def test_relevance_service_extracts_search_and_item_features() -> None:
    service = RelevanceService(repository=FakeRepository())
    saved_search = _saved_search(
        required_keywords="charizard", excluded_keywords="proxy"
    )
    item = _item(title="Pokemon Charizard 1999 Holo", price="125.50")

    features = service.extract_features(saved_search, item)

    assert features["query_text"] == "pokemon charizard"
    assert features["required_keywords_present"] is True
    assert features["excluded_keywords_present"] is False
    assert features["query_match_ratio"] == 1.0
    assert features["price"] == Decimal("125.50")


def test_relevance_service_keeps_required_keywords_as_hard_filter() -> None:
    service = RelevanceService(repository=FakeRepository())
    saved_search = _saved_search(required_keywords="charizard")
    item = _item(title="Pokemon Blastoise Holo")

    decision = service.should_notify(user_id=1, saved_search=saved_search, item=item)

    assert decision.should_notify is False
    assert decision.score == 0.0
    assert decision.reasons == ("missing_required_keywords",)


def test_relevance_service_keeps_excluded_keywords_as_hard_filter() -> None:
    service = RelevanceService(repository=FakeRepository(Feedback(is_relevant=True)))
    saved_search = _saved_search(excluded_keywords="proxy")
    item = _item(title="Pokemon Charizard proxy card")

    decision = service.should_notify(user_id=1, saved_search=saved_search, item=item)

    assert decision.should_notify is False
    assert decision.reasons == ("excluded_keywords_present",)


def test_relevance_service_default_scorer_passes_through_after_hard_filters() -> None:
    """Default scorer notifies any item that survives hard filters."""
    service = RelevanceService(repository=FakeRepository())
    saved_search = _saved_search()
    item = _item(title="Pokemon Charizard Holo")

    decision = service.should_notify(user_id=1, saved_search=saved_search, item=item)

    assert decision.should_notify is True
    assert decision.reasons == ("pass_through",)


def test_relevance_service_does_not_consult_legacy_feedback_override() -> None:
    """Negative legacy feedback no longer suppresses notifications post-filter."""
    service = RelevanceService(
        repository=FakeRepository(Feedback(is_relevant=False))
    )
    saved_search = _saved_search()
    item = _item(title="Pokemon Charizard Holo")

    decision = service.should_notify(user_id=1, saved_search=saved_search, item=item)

    assert decision.should_notify is True
    assert decision.reasons == ("pass_through",)


def test_relevance_service_scores_matching_items_with_baseline_heuristic() -> None:
    service = RelevanceService(
        repository=FakeRepository(), scorer=BaselineRelevanceScorer()
    )
    saved_search = _saved_search()
    item = _item(title="Pokemon Charizard Holo")

    decision = service.should_notify(user_id=1, saved_search=saved_search, item=item)

    assert decision.should_notify is True
    assert decision.score == 1.0
    assert "query_terms_matched" in decision.reasons


def test_relevance_service_penalizes_likely_accessory_items() -> None:
    service = RelevanceService(
        repository=FakeRepository(), scorer=BaselineRelevanceScorer()
    )
    saved_search = _saved_search()
    item = _item(title="Pokemon Charizard card case")

    decision = service.should_notify(user_id=1, saved_search=saved_search, item=item)

    assert decision.should_notify is True
    assert decision.score == 0.65
    assert "likely_accessory" in decision.reasons


def test_relevance_service_records_interactions_through_repository() -> None:
    repository = FakeRepository()
    service = RelevanceService(repository=repository)

    result = service.record_interaction(
        user_id=1,
        search_id="search-1",
        item_id="item-1",
        interaction_type="onboarding_label",
        label="relevant",
        source="preview",
    )

    assert result == repository.recorded_interactions[0]
    assert repository.recorded_interactions[0]["label"] == "relevant"


def test_non_bool_onboarding_label_persists_through_interaction_repository() -> None:
    interaction_repository = FakeInteractionRepository()
    repository = SqlAlchemyRelevanceRepository(
        session=FakeSession(),
        interaction_repository=interaction_repository,
    )

    result = repository.record_interaction(
        user_id=1,
        search_id="search-1",
        item_id="item-1",
        interaction_type="onboarding_label",
        label="maybe",
        source="preview",
    )

    assert isinstance(result, RelevanceInteraction)
    assert result.persisted is True
    assert interaction_repository.recorded_payloads == [
        {
            "user_id": 1,
            "query_id": "search-1",
            "item_id": "item-1",
            "interaction_type": "onboarding_label",
            "label": "maybe",
            "source": "preview",
            "metadata_json": {"search_id": "search-1"},
        }
    ]


def test_legacy_feedback_fallback_still_persists_bool_label(monkeypatch) -> None:
    session = FakeSession()
    query = SimpleNamespace(
        keyword_id=10,
        required_keywords="charizard",
        excluded_keywords="proxy",
    )
    feedback_lookup = FakeLookup(result=None)
    monkeypatch.setattr(
        relevance_repository,
        "UserQuery",
        SimpleNamespace(query=FakeLookup(result=query)),
    )
    monkeypatch.setattr(
        relevance_repository,
        "ItemRelevanceFeedback",
        FakeFeedbackModel(feedback_lookup),
    )

    repository = SqlAlchemyRelevanceRepository(session=session)

    result = repository.record_interaction(
        user_id=1,
        search_id="search-1",
        item_id="item-1",
        interaction_type="onboarding_label",
        label="relevant",
        source="preview",
    )

    assert isinstance(result, RelevanceInteraction)
    assert result.persisted is True
    assert session.flush_count == 1
    assert len(session.added) == 1
    assert session.added[0].is_relevant is True
    assert session.added[0].required_keywords == "charizard"
    assert session.added[0].excluded_keywords == "proxy"


def test_should_notify_behavior_is_unchanged_by_interaction_support() -> None:
    """Adding interaction recording must not change the live decision path."""
    service = RelevanceService(repository=FakeRepository(Feedback(is_relevant=False)))
    saved_search = _saved_search()
    item = _item(title="Pokemon Charizard Holo")

    decision = service.should_notify(user_id=1, saved_search=saved_search, item=item)

    # Default scorer is pass-through; legacy feedback is no longer consulted.
    assert decision.should_notify is True
    assert decision.reasons == ("pass_through",)


def _saved_search(
    required_keywords: str | None = None,
    excluded_keywords: str | None = None,
) -> SavedSearch:
    return SavedSearch(
        id="search-1",
        user_id=1,
        keyword_id=10,
        keywords="pokemon charizard",
        marketplace="EBAY_GB",
        is_active=True,
        filters=SearchFilters(
            min_price=10,
            max_price=500,
            item_location="GB",
            condition="USED",
            required_keywords=required_keywords,
            excluded_keywords=excluded_keywords,
        ),
    )


def _item(title: str, price: str = "100") -> dict[str, Any]:
    return {
        "item_id": "item-1",
        "title": title,
        "price": price,
        "condition": "USED",
        "location": {"country": "GB"},
        "buying_options": "FIXED_PRICE",
    }


class FakeInteractionRepository:
    def __init__(self) -> None:
        self.recorded_payloads: list[dict[str, Any]] = []

    def values(self, **payload: Any) -> dict[str, Any]:
        return payload

    def add(self, payload: dict[str, Any]) -> object:
        self.recorded_payloads.append(payload)
        return payload

    def record_interaction(self, **payload: Any) -> object:
        self.recorded_payloads.append(payload)
        return payload


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.flush_count = 0

    def add(self, value: Any) -> None:
        self.added.append(value)

    def flush(self) -> None:
        self.flush_count += 1


class FakeLookup:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.filters: dict[str, Any] | None = None

    def filter_by(self, **filters: Any) -> "FakeLookup":
        self.filters = filters
        return self

    def one_or_none(self) -> Any:
        return self.result


class FakeFeedbackModel:
    def __init__(self, query: FakeLookup) -> None:
        self.query = query

    def __call__(self, **kwargs: Any) -> Any:
        return SimpleNamespace(**kwargs)
