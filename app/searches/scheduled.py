"""Scheduler-facing service that orchestrates a single scrape pass.

Two cadences are exposed: a cheap recent pass (newly listed items) and a
heavier full pass (catalogue refresh). Both share the same processing
pipeline; the ``ScrapeStrategy`` they receive determines breadth and ordering.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.extensions import db
from app.repositories import UserQueryRepository
from app.searches.item_processor import process_items
from app.searches.mapping import saved_search_from_model
from app.searches.strategies import (
    FullScrapeStrategy,
    RecentScrapeStrategy,
    ScrapeKind,
    ScrapeOutcome,
    ScrapeStrategy,
)

FULL_SCRAPE_INTERVAL = timedelta(hours=24)

logger = logging.getLogger(__name__)


class ScheduledQueryService:
    """Run a saved search on a given cadence and persist the resulting state."""

    def __init__(
        self,
        query_repository: Any | None = None,
        full_strategy: ScrapeStrategy | None = None,
        recent_strategy: ScrapeStrategy | None = None,
        item_processor: Callable[..., Any] | None = None,
        run_recorder: Any | None = None,
        session: Any | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.queries = query_repository or UserQueryRepository()
        self.full_strategy = full_strategy or FullScrapeStrategy()
        self.recent_strategy = recent_strategy or RecentScrapeStrategy()
        self.item_processor = item_processor or process_items
        self.run_recorder = run_recorder
        self.session = session or db.session
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def run_full_scrape(self, query_id: str) -> None:
        """Execute the heavy catalogue-refresh pass."""
        print(f"FULL_SCRAPE_JOB: Query ID: {query_id}")
        self._run(query_id, self.full_strategy, self._finish_full)

    def run_recent_scrape(self, query_id: str) -> None:
        """Execute the cheap newly-listed pass."""
        print(f"RECENT_SCRAPE_JOB: Query ID: {query_id}")
        self._run(query_id, self.recent_strategy, self._finish_recent)

    def _run(
        self,
        query_id: str,
        strategy: ScrapeStrategy,
        finish: Callable[[Any], None],
    ) -> None:
        query = self.queries.get_active(query_id)
        if not query:
            self._log_aborted(query_id)
            return

        run = self._start_run(query, strategy.kind)
        try:
            outcome = self._execute_strategy(query, strategy)
            self._process(outcome, query)
            finish(query)
            self._finish_run_success(run, len(outcome.items))
            self.session.commit()
        except Exception as exc:
            self._finish_run_failure(run, exc)
            raise

    def _execute_strategy(
        self, query: Any, strategy: ScrapeStrategy
    ) -> ScrapeOutcome:
        saved_search = saved_search_from_model(query)
        return strategy.execute(saved_search)

    def _process(self, outcome: ScrapeOutcome, query: Any) -> None:
        self.item_processor(
            outcome.items,
            query,
            full_scan=outcome.kind is ScrapeKind.FULL,
            check_existing=outcome.kind is ScrapeKind.FULL,
            notify=True,
            first_run=bool(query.first_run),
        )

    def _finish_full(self, query: Any) -> None:
        now = self.clock()
        query.first_run = False
        query.last_full_run = now
        query.next_full_run = now + FULL_SCRAPE_INTERVAL

    def _finish_recent(self, query: Any) -> None:
        query.last_recent_run = self.clock()

    def _start_run(self, query: Any, kind: ScrapeKind) -> Any | None:
        if not self.run_recorder:
            return None
        return self.run_recorder.start(query=query, run_type=kind.value)

    def _finish_run_success(self, run: Any | None, item_count: int) -> None:
        if run is not None:
            self.run_recorder.finish_success(run, item_count=item_count)

    def _finish_run_failure(self, run: Any | None, exc: Exception) -> None:
        if run is None:
            return
        self.session.rollback()
        self.run_recorder.finish_failure(run, error=str(exc))
        self.session.commit()

    @staticmethod
    def _log_aborted(query_id: str) -> None:
        logger.debug("[Job %s] Aborting - no active query", query_id)
