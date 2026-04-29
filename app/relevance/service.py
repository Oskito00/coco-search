from typing import Any

from app.relevance.domain import RelevanceDecision
from app.relevance.features import extract_item_features
from app.relevance.repository import RelevanceRepository, SqlAlchemyRelevanceRepository
from app.relevance.scoring import PassThroughScorer, RelevanceScorer


class RelevanceService:
    """Facade for feature extraction, feedback capture, and relevance decisions."""

    def __init__(
        self,
        repository: RelevanceRepository | None = None,
        scorer: RelevanceScorer | None = None,
    ) -> None:
        self.repository = repository or SqlAlchemyRelevanceRepository()
        self.scorer = scorer or PassThroughScorer()

    def extract_features(self, saved_search: Any, item: Any) -> dict[str, Any]:
        """Extract model-ready features from a saved search and item."""

        return extract_item_features(saved_search, item)

    def record_interaction(
        self,
        user_id: int,
        search_id: str,
        item_id: str,
        interaction_type: str,
        label: str | None = None,
        source: str | None = None,
    ) -> object:
        """Record an onboarding or result interaction through the repository."""

        return self.repository.record_interaction(
            user_id=user_id,
            search_id=search_id,
            item_id=item_id,
            interaction_type=interaction_type,
            label=label,
            source=source,
        )

    def should_notify(
        self,
        user_id: int,
        saved_search: Any,
        item: Any,
    ) -> RelevanceDecision:
        """Apply hard filters then defer to the configured scorer.

        Legacy thumbs-up/down feedback is no longer consulted here — the
        future ML scorer should derive that signal from
        ``UserItemInteraction`` instead.
        """

        features = self.extract_features(saved_search, item)
        hard_filter_reasons = _hard_filter_failures(features)
        if hard_filter_reasons:
            return RelevanceDecision(
                score=0.0,
                should_notify=False,
                reasons=tuple(hard_filter_reasons),
                features=features,
            )
        return self.scorer.score_features(features)


def _hard_filter_failures(features: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not features["required_keywords_present"]:
        failures.append("missing_required_keywords")
    if features["excluded_keywords_present"]:
        failures.append("excluded_keywords_present")
    if not _price_matches(features):
        failures.append("price_outside_range")
    if not _condition_matches(features):
        failures.append("condition_mismatch")
    if not _location_matches(features):
        failures.append("location_mismatch")
    if not _buying_options_match(features):
        failures.append("buying_options_mismatch")
    return failures


def _price_matches(features: dict[str, Any]) -> bool:
    price = features["price"]
    if price is None:
        return features["min_price"] is None and features["max_price"] is None
    min_price = features["min_price"]
    max_price = features["max_price"]
    if min_price is not None and price < min_price:
        return False
    if max_price is not None and price > max_price:
        return False
    return True


def _condition_matches(features: dict[str, Any]) -> bool:
    expected = features["expected_condition"]
    actual = features["condition"]
    return expected is None or actual is None or actual == expected


def _location_matches(features: dict[str, Any]) -> bool:
    expected = features["expected_location"]
    actual = features["location_country"]
    if expected in (None, "ANY"):
        return True
    return actual is None or actual == expected


def _buying_options_match(features: dict[str, Any]) -> bool:
    expected = features["expected_buying_options"]
    actual = features["buying_options"]
    if expected in (None, "FIXED_PRICE|AUCTION"):
        return True
    return actual is None or expected in actual.split("|")
