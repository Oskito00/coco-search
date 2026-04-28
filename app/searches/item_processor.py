from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.notifications import EventNotificationService
from app.repositories import ItemRepository
from app.searches.events import SearchProcessingResult


class SearchItemProcessor:
    def __init__(self, item_repository=None, notification_service=None):
        self.items = item_repository or ItemRepository()
        self.notifications = notification_service or EventNotificationService()

    def process(
        self,
        items,
        query,
        check_existing=False,
        full_scan=False,
        notify=True,
        first_run=False,
    ):
        result = SearchProcessingResult()
        current_time = datetime.now(timezone.utc)
        keyword = query.keyword

        for item_data in items:
            item = self._upsert_item_for_query(
                item_data=item_data,
                query=query,
                keyword=keyword,
                result=result,
                current_time=current_time,
                first_run=first_run,
            )

            if item is not None:
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

    def _upsert_item_for_query(self, item_data, query, keyword, result, current_time, first_run):
        print(f"[Process Items] Starting item processing for query {query.query_id}")
        existing = self.items.get_by_ebay_id(item_data["ebay_id"])

        if existing:
            feedback = self.items.get_feedback(
                user_id=query.user_id,
                item_id=existing.item_id,
                keyword_id=keyword.keyword_id,
            )
            self.items.link_keyword(keyword.keyword_id, existing.item_id)

            if feedback and feedback.is_relevant is False:
                return None

            link = self.items.link_query(
                query.query_id,
                existing.item_id,
                created_at=current_time,
            )
            if link and not first_run:
                result.new_items.append(existing)

            old_price = existing.price
            if self.items.update_item(existing, item_data, current_time):
                result.updated_items.append(existing)

            new_price = item_data.get("price")
            if new_price and old_price and new_price < old_price:
                result.price_drops.append(
                    {
                        "item": existing,
                        "old_price": old_price,
                        "new_price": new_price,
                    }
                )

            return existing

        new_item = self.items.create_item(item_data)
        self.items.link_keyword(keyword.keyword_id, new_item.item_id, found_at=current_time)
        self.items.link_query(query.query_id, new_item.item_id, created_at=current_time)

        if not first_run:
            result.new_items.append(new_item)

        return new_item

    def _track_ending_auction(self, item, item_data, query, result, current_time):
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


def process_items(items, query, check_existing=False, full_scan=False, notify=True, first_run=False):
    result = SearchItemProcessor().process(
        items=items,
        query=query,
        check_existing=check_existing,
        full_scan=full_scan,
        notify=notify,
        first_run=first_run,
    )
    return result.new_items, result.updated_items
