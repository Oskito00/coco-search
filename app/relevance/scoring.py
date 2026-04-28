from dataclasses import dataclass
import re

from app.utils.text_helpers import remove_accents


ACCESSORY_TERMS = {
    "case",
    "cases",
    "cover",
    "covers",
    "protector",
    "screen",
    "charger",
    "cable",
    "mount",
    "holder",
}


@dataclass(frozen=True)
class RelevanceDecision:
    score: float
    should_notify: bool
    reasons: tuple = ()


class BaselineRelevanceScorer:
    """Small rules baseline that can later be replaced by a trained model."""

    def score(self, query_text, item):
        query_terms = _terms(query_text)
        title_terms = _terms(getattr(item, "title", None) or item.get("title", ""))

        if not query_terms:
            return RelevanceDecision(score=0.5, should_notify=True, reasons=("empty_query",))

        matched_terms = query_terms & title_terms
        score = len(matched_terms) / len(query_terms)
        reasons = []

        if matched_terms:
            reasons.append("query_terms_matched")

        if ACCESSORY_TERMS & title_terms and not ACCESSORY_TERMS & query_terms:
            score -= 0.35
            reasons.append("likely_accessory")

        score = max(0.0, min(1.0, score))
        return RelevanceDecision(
            score=score,
            should_notify=score >= 0.5,
            reasons=tuple(reasons),
        )


def _terms(text):
    normalised = remove_accents((text or "").lower())
    return set(re.findall(r"[a-z0-9]+", normalised))
