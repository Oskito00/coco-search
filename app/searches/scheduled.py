from datetime import datetime, timedelta, timezone

from app.extensions import db, scheduler
from app.repositories import UserQueryRepository
from app.searches.execution import scrape_ebay, scrape_new_items
from app.searches.item_processor import process_items

FULL_SCRAPE_INTERVAL = timedelta(hours=24)


class ScheduledQueryService:
    def __init__(
        self,
        query_repository=None,
        full_search=None,
        recent_search=None,
        item_processor=None,
        run_recorder=None,
        session=None,
        clock=None,
    ):
        self.queries = query_repository or UserQueryRepository()
        self.full_search = full_search or scrape_ebay
        self.recent_search = recent_search or scrape_new_items
        self.item_processor = item_processor or process_items
        self.run_recorder = run_recorder
        self.session = session or db.session
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def run_full_scrape(self, query_id):
        print(f"FULL_SCRAPE_JOB: Query ID: {query_id}")
        self._run_scheduled_search(
            query_id=query_id,
            run_type="full",
            search=self.full_search,
            process=self._process_full_scrape,
            finish=self._finish_full_scrape,
        )

    def run_recent_scrape(self, query_id):
        print(f"RECENT_SCRAPE_JOB: Query ID: {query_id}")
        self._run_scheduled_search(
            query_id=query_id,
            run_type="recent",
            search=self.recent_search,
            process=self._process_recent_scrape,
            finish=self._finish_recent_scrape,
        )

    def _run_scheduled_search(self, query_id, run_type, search, process, finish):
        query = self.queries.get_active(query_id)
        if not query:
            scheduler.app.logger.debug("[Job %s] Aborting - no active query", query_id)
            return

        run = self._start_run(query, run_type)
        try:
            items = self._execute_search(query, search)
            process(items, query)
            finish(query)
            self._finish_run_success(run, len(items))
            self.session.commit()
        except Exception as exc:
            self._finish_run_failure(run, exc)
            raise

    def _execute_search(self, query, search):
        keyword = self.queries.get_keyword(query.keyword_id)
        return search(
            keyword.keyword_text,
            filters=_filters_for_query(query),
            required_keywords=query.required_keywords,
            excluded_keywords=query.excluded_keywords,
            marketplace=query.marketplace,
        )

    def _process_full_scrape(self, items, query):
        self.item_processor(
            items,
            query,
            full_scan=True,
            notify=True,
            first_run=query.first_run,
        )

    def _process_recent_scrape(self, items, query):
        self.item_processor(items, query, check_existing=False, notify=True)

    def _finish_full_scrape(self, query):
        now = self.clock()
        query.first_run = False
        query.last_full_run = now
        query.next_full_run = now + FULL_SCRAPE_INTERVAL

    def _finish_recent_scrape(self, query):
        query.last_recent_run = self.clock()

    def _start_run(self, query, run_type):
        if not self.run_recorder:
            return None
        return self.run_recorder.start(query=query, run_type=run_type)

    def _finish_run_success(self, run, item_count):
        if run is not None:
            self.run_recorder.finish_success(run, item_count=item_count)

    def _finish_run_failure(self, run, exc):
        if run is not None:
            self.session.rollback()
            self.run_recorder.finish_failure(run, error=str(exc))
            self.session.commit()


def _filters_for_query(query):
    return {
        "min_price": query.min_price,
        "max_price": query.max_price,
        "item_location": query.item_location,
        "condition": query.condition,
        "buying_options": query.buying_options,
    }
