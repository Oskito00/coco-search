from typing import Any, Protocol

from app.relevance.domain import RelevanceDecision
from app.relevance.features import extract_item_features, terms


class RelevanceScorer(Protocol):
    """Inference contract for baseline or trained relevance scorers."""

    def score_features(self, features: dict[str, Any]) -> RelevanceDecision:
        """Score extracted features and return a notification decision."""


class BaselineRelevanceScorer:
    """Small rules baseline that can later be replaced by a trained model."""

    threshold = 0.5

    def score(self, query_text: str, item: Any) -> RelevanceDecision:
        """Compatibility API for callers that score a query and item directly."""

        title = getattr(item, "title", None)
        if title is None and isinstance(item, dict):
            title = item.get("title", "")
        query_terms = terms(query_text)
        title_terms = terms(str(title or ""))
        query_match_ratio = 0.5
        if query_terms:
            query_match_ratio = len(query_terms & title_terms) / len(query_terms)

        features: dict[str, Any] = {
            "query_terms": query_terms,
            "title_terms": title_terms,
            "query_match_ratio": query_match_ratio,
            "query_term_match_count": len(query_terms & title_terms),
            "accessory_terms_present": False,
            "query_has_accessory_terms": False,
        }
        return self.score_features(features)

    def score_search_item(self, saved_search: Any, item: Any) -> RelevanceDecision:
        """Score an item after extracting saved-search aware features."""

        return self.score_features(extract_item_features(saved_search, item))

    def score_features(self, features: dict[str, Any]) -> RelevanceDecision:
        """Score precomputed relevance features without side effects."""

        query_terms = features.get("query_terms") or set()
        score = float(features.get("query_match_ratio") or 0.0)
        reasons: list[str] = []
        if not query_terms:
            return RelevanceDecision(
                score=0.5,
                should_notify=True,
                reasons=("empty_query",),
                features=features,
            )

        if features.get("query_term_match_count", 0) > 0 or score > 0:
            reasons.append("query_terms_matched")

        if features.get("accessory_terms_present") and not features.get(
            "query_has_accessory_terms"
        ):
            score -= 0.35
            reasons.append("likely_accessory")

        score = max(0.0, min(1.0, score))
        return RelevanceDecision(
            score=score,
            should_notify=score >= self.threshold,
            reasons=tuple(reasons),
            features=features,
        )
