from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from app.extensions import db
from app.items.normalization import normalize_item_payload
from app.notifications import EventNotificationService
from app.repositories import ItemRepository
from app.searches.events import (
    DomainEvent,
    SearchProcessingResult,
    build_auction_ending_soon_event,
    build_item_discovered_event,
    build_item_updated_event,
    build_price_dropped_event,
)

ITEM_DIFF_FIELDS = (
    "title",
    "price",
    "current_bid",
    "current_bid_currency",
    "currency",
    "url",
    "image_url",
    "seller",
    "seller_rating",
    "condition",
    "location_country",
    "postal_code",
    "start_time",
    "end_time",
    "buying_options",
    "auction_details",
    "categories",
    "marketplace",
    "images",
)

OBSERVATION_HOOKS = (
    "record_item_observation",
    "store_item_observation",
    "write_item_observation",
    "record_observation",
)

EVENT_HOOKS = (
    "record_domain_event",
    "store_domain_event",
    "emit_domain_event",
    "record_event",
    "store_event",
    "emit_event",
)


class SearchItemProcessor:
    def __init__(
        self,
        item_repository: Any = None,
        notification_service: Any = None,
        event_repository: Any = None,
        observation_repository: Any = None,
    ) -> None:
        self.items = item_repository or ItemRepository()
        self.notifications = notification_service or EventNotificationService()
        self.events = event_repository or self.items
        self.observations = observation_repository or self.items

    def process(
        self,
        items: Iterable[dict[str, Any]],
        query: Any,
        check_existing: bool = False,
        full_scan: bool = False,
        notify: bool = True,
        first_run: bool = False,
    ) -> SearchProcessingResult:
        result = SearchProcessingResult()
        current_time = datetime.now(timezone.utc)
        keyword = query.keyword

        for raw_item_data in items:
            item_data = normalize_item_payload(raw_item_data)
            item = self._upsert_item_for_query(
                item_data=item_data,
                query=query,
                keyword=keyword,
                result=result,
                current_time=current_time,
                first_run=first_run,
            )

            if item is not None:
                self._record_observation(item, item_data, query, current_time)
                self._track_ending_auction(item, item_data, query, result, current_time)

        try:
            db.session.commit()
            if notify:
                self.notifications.notify_search_events(query, result)
            print(f"Finished processing for query {query.query_id}")
            return result
        except Exception as e:
            print(f"[Process Items] Database commit failed: {str(e)}")
            db.session.rollback()
            raise

    def _upsert_item_for_query(
        self,
        item_data: dict[str, Any],
        query: Any,
        keyword: Any,
        result: SearchProcessingResult,
        current_time: datetime,
        first_run: bool,
    ) -> Any | None:
        print(f"[Process Items] Starting item processing for query {query.query_id}")
        ebay_id = item_data.get("ebay_id")
        if not ebay_id:
            raise ValueError("Cannot process item payload without ebay_id")

        existing = self.items.get_by_ebay_id(ebay_id)

        if existing:
            return self._process_existing_item(
                existing,
                item_data,
                query,
                keyword,
                result,
                current_time,
                first_run,
            )

        return self._process_new_item(
            item_data, query, keyword, result, current_time, first_run
        )

    def _process_existing_item(
        self,
        item: Any,
        item_data: dict[str, Any],
        query: Any,
        keyword: Any,
        result: SearchProcessingResult,
        current_time: datetime,
        first_run: bool,
    ) -> Any | None:
        feedback = self.items.get_feedback(
            user_id=query.user_id,
            item_id=item.item_id,
            keyword_id=keyword.keyword_id,
        )
        self.items.link_keyword(keyword.keyword_id, item.item_id)

        if feedback and feedback.is_relevant is False:
            return None

        link = self.items.link_query(
            query.query_id, item.item_id, created_at=current_time
        )
        if link and not first_run:
            self._record_new_item(item, query, result, current_time)

        old_price = getattr(item, "price", None)
        item_changes = _diff_item(item, item_data)
        if self.items.update_item(item, item_data, current_time):
            result.updated_items.append(item)
            self._record_event(
                build_item_updated_event(query, item, current_time, item_changes),
                result,
            )

        price_drop_values = _price_drop_values(old_price, item_data.get("price"))
        if price_drop_values:
            old_price_value, new_price_value = price_drop_values
            price_drop = {
                "item": item,
                "old_price": old_price_value,
                "new_price": new_price_value,
            }
            result.price_drops.append(price_drop)
            self._record_event(
                build_price_dropped_event(
                    query,
                    item,
                    current_time,
                    old_price_value,
                    new_price_value,
                ),
                result,
            )

        return item

    def _process_new_item(
        self,
        item_data: dict[str, Any],
        query: Any,
        keyword: Any,
        result: SearchProcessingResult,
        current_time: datetime,
        first_run: bool,
    ) -> Any:
        item = self.items.create_item(item_data)
        self.items.link_keyword(keyword.keyword_id, item.item_id, found_at=current_time)
        self.items.link_query(query.query_id, item.item_id, created_at=current_time)

        if not first_run:
            self._record_new_item(item, query, result, current_time)

        return item

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

    def _track_ending_auction(
        self,
        item: Any,
        item_data: dict[str, Any],
        query: Any,
        result: SearchProcessingResult,
        current_time: datetime,
    ) -> None:
        end_time = item_data.get("end_time")
        if not end_time:
            return

        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        if (end_time - current_time) >= timedelta(hours=12):
            return

        user_query_item = self.items.get_query_item(query.query_id, item.item_id)
        if user_query_item and not user_query_item.auction_ending_notification_sent:
            result.ending_auctions.append(item)
            user_query_item.auction_ending_notification_sent = True
            self._record_event(
                build_auction_ending_soon_event(query, item, current_time, end_time),
                result,
            )

    def _record_observation(
        self,
        item: Any,
        item_data: dict[str, Any],
        query: Any,
        observed_at: datetime,
    ) -> None:
        observation = {
            "user_id": getattr(query, "user_id", None),
            "search_id": getattr(query, "query_id", None),
            "item_id": getattr(item, "item_id", None),
            "ebay_id": item_data.get("ebay_id"),
            "observed_at": observed_at,
            "price": item_data.get("price"),
            "currency": item_data.get("currency"),
            "payload": item_data,
        }
        _call_optional_repository_hook(
            self.observations, OBSERVATION_HOOKS, observation
        )

    def _record_event(self, event: DomainEvent, result: SearchProcessingResult) -> None:
        result.domain_events.append(event)
        _call_optional_repository_hook(self.events, EVENT_HOOKS, event)


def _diff_item(item: Any, item_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    changes = {}
    for field in ITEM_DIFF_FIELDS:
        if field not in item_data or not hasattr(item, field):
            continue
        old_value = getattr(item, field)
        new_value = item_data[field]
        if old_value != new_value:
            changes[field] = {"old": old_value, "new": new_value}
    return changes


def _price_drop_values(old_price: Any, new_price: Any) -> tuple[float, float] | None:
    if old_price is None or new_price is None or new_price >= old_price:
        return None
    return float(old_price), float(new_price)


def _call_optional_repository_hook(
    repository: Any,
    hook_names: tuple[str, ...],
    payload: Any,
) -> Any | None:
    for hook_name in hook_names:
        hook = getattr(repository, hook_name, None)
        if callable(hook):
            return hook(payload)
    return None


def process_items(
    items: Iterable[dict[str, Any]],
    query: Any,
    check_existing: bool = False,
    full_scan: bool = False,
    notify: bool = True,
    first_run: bool = False,
) -> tuple[list[Any], list[Any]]:
    result = SearchItemProcessor().process(
        items=items,
        query=query,
        check_existing=check_existing,
        full_scan=full_scan,
        notify=notify,
        first_run=first_run,
    )
    return result.new_items, result.updated_items
