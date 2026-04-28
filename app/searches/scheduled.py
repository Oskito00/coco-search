from datetime import datetime, timedelta, timezone

from app.extensions import db, scheduler
from app.repositories import UserQueryRepository
from app.searches.execution import scrape_ebay, scrape_new_items
from app.searches.item_processor import process_items


class ScheduledQueryService:
    def __init__(self, query_repository=None):
        self.queries = query_repository or UserQueryRepository()

    def run_full_scrape(self, query_id):
        print(f"FULL_SCRAPE_JOB: Query ID: {query_id}")
        query = self.queries.get_active(query_id)
        if not query:
            scheduler.app.logger.debug("[Job %s] Aborting - no active query", query_id)
            return

        keyword = self.queries.get_keyword(query.keyword_id)
        items = scrape_ebay(
            keyword.keyword_text,
            filters=_filters_for_query(query),
            required_keywords=query.required_keywords,
            excluded_keywords=query.excluded_keywords,
            marketplace=query.marketplace,
        )

        process_items(
            items,
            query,
            full_scan=True,
            notify=True,
            first_run=query.first_run,
        )
        query.first_run = False
        query.last_full_run = datetime.now(timezone.utc)
        query.next_full_run = datetime.now(timezone.utc) + timedelta(hours=24)
        db.session.commit()

    def run_recent_scrape(self, query_id):
        print(f"RECENT_SCRAPE_JOB: Query ID: {query_id}")
        query = self.queries.get_active(query_id)
        if not query:
            print(f"[Job {query_id}] Aborting - no active query")
            return

        keyword = self.queries.get_keyword(query.keyword_id)
        items = scrape_new_items(
            keyword.keyword_text,
            filters=_filters_for_query(query),
            required_keywords=query.required_keywords,
            excluded_keywords=query.excluded_keywords,
            marketplace=query.marketplace,
        )
        process_items(items, query, check_existing=False, notify=True)
        query.last_recent_run = datetime.now(timezone.utc)
        db.session.commit()


def _filters_for_query(query):
    return {
        "min_price": query.min_price,
        "max_price": query.max_price,
        "item_location": query.item_location,
        "condition": query.condition,
        "buying_options": query.buying_options,
    }
