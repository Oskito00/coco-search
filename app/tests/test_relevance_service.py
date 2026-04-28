from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.relevance import RelevanceService


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


def test_relevance_service_uses_explicit_irrelevant_feedback() -> None:
    service = RelevanceService(repository=FakeRepository(Feedback(is_relevant=False)))
    saved_search = _saved_search()
    item = _item(title="Pokemon Charizard Holo")

    decision = service.should_notify(user_id=1, saved_search=saved_search, item=item)

    assert decision.should_notify is False
    assert decision.score == 0.0
    assert decision.reasons == ("user_marked_irrelevant",)


def test_relevance_service_scores_matching_items_with_baseline_heuristic() -> None:
    service = RelevanceService(repository=FakeRepository())
    saved_search = _saved_search()
    item = _item(title="Pokemon Charizard Holo")

    decision = service.should_notify(user_id=1, saved_search=saved_search, item=item)

    assert decision.should_notify is True
    assert decision.score == 1.0
    assert "query_terms_matched" in decision.reasons


def test_relevance_service_penalizes_likely_accessory_items() -> None:
    service = RelevanceService(repository=FakeRepository())
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
