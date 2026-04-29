"""Internal collaborators for :mod:`app.searches.item_processor`.

The orchestrator composes these single-purpose pieces. Each module is small,
pure where possible, and individually testable.
"""

from app.searches.processing.auction import AUCTION_ALERT_WINDOW, is_ending_within
from app.searches.processing.differ import diff_item, detect_price_drop
from app.searches.processing.event_recorder import EventRecorder, NoopEventRecorder
from app.searches.processing.feature_recorder import (
    FEATURE_VERSION,
    FeatureSnapshotContext,
    FeatureSnapshotRecorder,
    NoopFeatureSnapshotRecorder,
)
from app.searches.processing.observation_recorder import (
    NoopObservationRecorder,
    ObservationContext,
    ObservationRecorder,
)
from app.searches.processing.serialization import serialize_for_persistence

__all__ = [
    "AUCTION_ALERT_WINDOW",
    "EventRecorder",
    "FEATURE_VERSION",
    "FeatureSnapshotContext",
    "FeatureSnapshotRecorder",
    "NoopEventRecorder",
    "NoopFeatureSnapshotRecorder",
    "NoopObservationRecorder",
    "ObservationContext",
    "ObservationRecorder",
    "detect_price_drop",
    "diff_item",
    "is_ending_within",
    "serialize_for_persistence",
]
