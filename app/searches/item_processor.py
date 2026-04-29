"""Search item processor: orchestrate per-item upsert, diff, and event capture.

The orchestrator delegates to the small collaborators in
:mod:`app.searches.processing`. Each public method on this class has a single
responsibility; persistence specifics live in the recorders, comparisons in
``differ``, the auction-window check in ``auction``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from app.extensions import db
from app.items.normalization import normalize_item_payload
from app.notifications import EventNotificationService
from app.repositories import (
    DomainEventRepository,
    ItemFeatureSnapshotRepository,
    ItemObservationRepository,
    ItemRepository,
)
from app.searches.events import (
    DomainEvent,
    SearchProcessingResult,
    build_auction_ending_soon_event,
    build_item_discovered_event,
    build_item_updated_event,
    build_price_dropped_event,
)
from app.searches.mapping import saved_search_from_model
from app.searches.processing import (
    EventRecorder,
    FeatureSnapshotContext,
    FeatureSnapshotRecorder,
    NoopEventRecorder,
    NoopFeatureSnapshotRecorder,
    NoopObservationRecorder,
    ObservationContext,
    ObservationRecorder,
    detect_price_drop,
    diff_item,
    is_ending_within,
)
from app.searches.processing.observation_recorder import build_observation_payload


@dataclass(frozen=True)
class ItemProcessingOutcome:
    """Per-item result reported up to the orchestrator's outer loop."""

    item: Any
    is_new_item: bool
    hard_filter_passed: bool = True


class SearchItemProcessor:
    """Apply a scrape's items to the database and emit derived domain events."""

    def __init__(
        self,
        item_repository: Any | None = None,
        notification_service: Any | None = None,
        event_repository: Any | None = None,
        observation_repository: Any | None = None,
        feature_repository: Any | None = None,
    ) -> None:
        self.items = item_repository or ItemRepository()
        self.notifications = notification_service or EventNotificationService()
        self.event_recorder = _resolve_event_recorder(event_repository)
        self.observation_recorder = _resolve_observation_recorder(
            observation_repository
        )
        self.feature_recorder = _resolve_feature_recorder(feature_repository)

    def process(
        self,
        items: Iterable[dict[str, Any]],
        query: Any,
        check_existing: bool = False,
        full_scan: bool = False,
        notify: bool = True,
        first_run: bool = False,
    ) -> SearchProcessingResult:
        """Process a batch of items, commit, and (optionally) trigger notifications."""
        result = SearchProcessingResult()
        current_time = datetime.now(timezone.utc)
        keyword = query.keyword

        for raw_item_data in items:
            self._handle_item(raw_item_data, query, keyword, result, current_time, first_run)

        return self._finalize(query, result, notify)

    def _handle_item(
        self,
        raw_item_data: dict[str, Any],
        query: Any,
        keyword: Any,
        result: SearchProcessingResult,
        current_time: datetime,
        first_run: bool,
    ) -> None:
        item_data = normalize_item_payload(raw_item_data)
        outcome = self._upsert(item_data, query, keyword, result, current_time, first_run)
        if outcome is None:
            return
        self._record_observation(outcome, item_data, query, current_time)
        self._record_feature_snapshot(outcome.item, query, current_time)
        self._track_ending_auction(outcome.item, item_data, query, result, current_time)

    def _finalize(
        self,
        query: Any,
        result: SearchProcessingResult,
        notify: bool,
    ) -> SearchProcessingResult:
        try:
            db.session.commit()
        except Exception as exc:
            print(f"[Process Items] Database commit failed: {exc}")
            db.session.rollback()
            raise
        if notify:
            self.notifications.notify_search_events(query, result)
        print(f"Finished processing for query {query.query_id}")
        return result

    def _upsert(
        self,
        item_data: dict[str, Any],
        query: Any,
        keyword: Any,
        result: SearchProcessingResult,
        current_time: datetime,
        first_run: bool,
    ) -> ItemProcessingOutcome | None:
        ebay_id = item_data.get("ebay_id")
        if not ebay_id:
            raise ValueError("Cannot process item payload without ebay_id")

        existing = self.items.get_by_ebay_id(ebay_id)
        if existing:
            return self._update_existing(
                existing, item_data, query, keyword, result, current_time, first_run
            )
        return self._create_new(item_data, query, keyword, result, current_time, first_run)

    def _update_existing(
        self,
        item: Any,
        item_data: dict[str, Any],
        query: Any,
        keyword: Any,
        result: SearchProcessingResult,
        current_time: datetime,
        first_run: bool,
    ) -> ItemProcessingOutcome | None:
        if self._suppressed_by_feedback(item, query, keyword):
            return None

        self.items.link_keyword(keyword.keyword_id, item.item_id)
        is_new_link = self.items.link_query(
            query.query_id, item.item_id, created_at=current_time
        ) is not None
        if is_new_link and not first_run:
            self._record_new_item(item, query, result, current_time)

        old_price = getattr(item, "price", None)
        item_changes = diff_item(item, item_data)
        if self.items.update_item(item, item_data, current_time):
            result.updated_items.append(item)
            self._record_event(
                build_item_updated_event(query, item, current_time, item_changes),
                result,
            )

        self._record_price_drop(
            item=item,
            old_price=old_price,
            new_price=item_data.get("price"),
            query=query,
            current_time=current_time,
            result=result,
        )
        return ItemProcessingOutcome(item=item, is_new_item=is_new_link)

    def _create_new(
        self,
        item_data: dict[str, Any],
        query: Any,
        keyword: Any,
        result: SearchProcessingResult,
        current_time: datetime,
        first_run: bool,
    ) -> ItemProcessingOutcome:
        item = self.items.create_item(item_data)
        self.items.link_keyword(keyword.keyword_id, item.item_id, found_at=current_time)
        self.items.link_query(query.query_id, item.item_id, created_at=current_time)
        if not first_run:
            self._record_new_item(item, query, result, current_time)
        return ItemProcessingOutcome(item=item, is_new_item=True)

    def _suppressed_by_feedback(self, item: Any, query: Any, keyword: Any) -> bool:
        feedback = self.items.get_feedback(
            user_id=query.user_id,
            item_id=item.item_id,
            keyword_id=keyword.keyword_id,
        )
        return feedback is not None and feedback.is_relevant is False

    def _record_new_item(
        self,
        item: Any,
        query: Any,
        result: SearchProcessingResult,
        current_time: datetime,
    ) -> None:
        result.new_items.append(item)
        self._record_event(
            build_item_discovered_event(query, item, current_time), result
        )

    def _record_price_drop(
        self,
        *,
        item: Any,
        old_price: Any,
        new_price: Any,
        query: Any,
        current_time: datetime,
        result: SearchProcessingResult,
    ) -> None:
        drop = detect_price_drop(old_price, new_price)
        if drop is None:
            return
        old_value, new_value = drop
        result.price_drops.append(
            {"item": item, "old_price": old_value, "new_price": new_value}
        )
        self._record_event(
            build_price_dropped_event(query, item, current_time, old_value, new_value),
            result,
        )

    def _track_ending_auction(
        self,
        item: Any,
        item_data: dict[str, Any],
        query: Any,
        result: SearchProcessingResult,
        current_time: datetime,
    ) -> None:
        end_time = item_data.get("end_time")
        if not is_ending_within(end_time, current_time):
            return
        link = self.items.get_query_item(query.query_id, item.item_id)
        if link is None or link.auction_ending_notification_sent:
            return
        result.ending_auctions.append(item)
        link.auction_ending_notification_sent = True
        self._record_event(
            build_auction_ending_soon_event(query, item, current_time, end_time),
            result,
        )

    def _record_observation(
        self,
        outcome: ItemProcessingOutcome,
        item_data: dict[str, Any],
        query: Any,
        observed_at: datetime,
    ) -> None:
        self.observation_recorder.record(
            ObservationContext(
                item=outcome.item,
                item_data=item_data,
                query=query,
                observed_at=observed_at,
                is_new_item=outcome.is_new_item,
                hard_filter_passed=outcome.hard_filter_passed,
            )
        )

    def _record_feature_snapshot(
        self,
        item: Any,
        query: Any,
        observed_at: datetime,
    ) -> None:
        try:
            saved_search = saved_search_from_model(query)
        except (AttributeError, ValueError):
            return
        self.feature_recorder.record(
            FeatureSnapshotContext(
                item=item,
                saved_search=saved_search,
                query=query,
                observed_at=observed_at,
            )
        )

    def _record_event(self, event: DomainEvent, result: SearchProcessingResult) -> None:
        result.domain_events.append(event)
        self.event_recorder.record(event)


def _resolve_event_recorder(repository: Any | None) -> Any:
    """Pick the event-recorder implementation: explicit, fake, or the real default."""
    if repository is None:
        return EventRecorder(DomainEventRepository())
    if _has_create(repository):
        return EventRecorder(repository)
    return _legacy_hook_recorder(repository, _LEGACY_EVENT_HOOKS) or NoopEventRecorder()


def _resolve_observation_recorder(repository: Any | None) -> Any:
    """Pick the observation-recorder implementation."""
    if repository is None:
        return ObservationRecorder(ItemObservationRepository())
    if _has_create(repository):
        return ObservationRecorder(repository)
    return (
        _legacy_hook_observation_recorder(repository) or NoopObservationRecorder()
    )


def _resolve_feature_recorder(repository: Any | None) -> Any:
    """Pick the feature-snapshot recorder implementation."""
    if repository is None:
        return FeatureSnapshotRecorder(ItemFeatureSnapshotRepository())
    if _has_create(repository):
        return FeatureSnapshotRecorder(repository)
    return NoopFeatureSnapshotRecorder()


def _has_create(repository: Any) -> bool:
    return callable(getattr(repository, "create", None))


_LEGACY_EVENT_HOOKS = (
    "record_domain_event",
    "store_domain_event",
    "emit_domain_event",
    "record_event",
    "store_event",
    "emit_event",
)

_LEGACY_OBSERVATION_HOOKS = (
    "record_item_observation",
    "store_item_observation",
    "write_item_observation",
    "record_observation",
)


def _legacy_hook_recorder(repository: Any, hook_names: tuple[str, ...]) -> Any | None:
    """Bridge older test fakes that record events via named hooks."""
    hook = _first_hook(repository, hook_names)
    if hook is None:
        return None

    class _HookEventRecorder:
        def record(self, event: DomainEvent) -> Any:
            return hook(event)

    return _HookEventRecorder()


def _legacy_hook_observation_recorder(repository: Any) -> Any | None:
    """Bridge older test fakes that record observations via named hooks."""
    hook = _first_hook(repository, _LEGACY_OBSERVATION_HOOKS)
    if hook is None:
        return None

    class _HookObservationRecorder:
        def record(self, context: ObservationContext) -> Any:
            return hook(build_observation_payload(context))

    return _HookObservationRecorder()


def _first_hook(repository: Any, hook_names: tuple[str, ...]) -> Any | None:
    for name in hook_names:
        hook = getattr(repository, name, None)
        if callable(hook):
            return hook
    return None


def process_items(
    items: Iterable[dict[str, Any]],
    query: Any,
    check_existing: bool = False,
    full_scan: bool = False,
    notify: bool = True,
    first_run: bool = False,
) -> tuple[list[Any], list[Any]]:
    """Legacy entry point that returns ``(new_items, updated_items)``."""
    result = SearchItemProcessor().process(
        items=items,
        query=query,
        check_existing=check_existing,
        full_scan=full_scan,
        notify=notify,
        first_run=first_run,
    )
    return result.new_items, result.updated_items
