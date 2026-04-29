"""Persist :class:`ItemFeatureSnapshot` rows alongside each processed item.

The snapshot captures the raw item-side and search-side features for one
``(query, item, run)`` triple. The orchestrator writes one row per item per
scrape; the relevance layer consumes the same dict shape at decision time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.relevance.features import (
    extract_raw_item_features,
    extract_raw_search_features,
)

FEATURE_VERSION = "raw-v1"


@dataclass(frozen=True)
class FeatureSnapshotContext:
    """Inputs needed to write one feature snapshot row."""

    item: Any
    saved_search: Any
    query: Any
    observed_at: datetime


class FeatureSnapshotRecorder:
    """Build the raw feature dict and write it through the repository."""

    def __init__(
        self, repository: Any, feature_version: str = FEATURE_VERSION
    ) -> None:
        self.repository = repository
        self.feature_version = feature_version

    def record(self, context: FeatureSnapshotContext) -> Any:
        item_id = getattr(context.item, "item_id", None)
        if item_id is None:
            return None
        features = {
            "item": extract_raw_item_features(context.item, now=context.observed_at),
            "search": extract_raw_search_features(context.saved_search),
        }
        return self.repository.create(
            item_id=item_id,
            query_id=getattr(context.query, "query_id", None),
            search_run_id=_search_run_id(context.query),
            features=features,
            feature_version=self.feature_version,
        )


class NoopFeatureSnapshotRecorder:
    """Recorder that intentionally drops snapshots (useful in tests / dry-runs)."""

    def record(self, context: FeatureSnapshotContext) -> None:
        return None


def _search_run_id(query: Any) -> Any:
    return (
        getattr(query, "search_run_id", None)
        or getattr(query, "current_search_run_id", None)
    )
