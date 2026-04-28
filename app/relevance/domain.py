from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RelevanceDecision:
    """Decision returned by relevance scoring before notification dispatch."""

    score: float
    should_notify: bool
    reasons: tuple[str, ...] = ()
    features: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelevanceInteraction:
    """Recorded interaction hook for future training data capture."""

    user_id: int
    search_id: str
    item_id: str
    interaction_type: str
    label: str | None = None
    source: str | None = None
    persisted: bool = False
