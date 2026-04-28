"""Functions executed by RQ workers. Each must be importable by string."""

from __future__ import annotations

import logging

from app.queue.runtime import with_app_context
from app.searches.scheduled import ScheduledQueryService

logger = logging.getLogger(__name__)


@with_app_context
def full_scrape(query_id: str) -> None:
    logger.info("FULL_SCRAPE %s", query_id)
    ScheduledQueryService().run_full_scrape(query_id)


@with_app_context
def recent_scrape(query_id: str) -> None:
    logger.info("RECENT_SCRAPE %s", query_id)
    ScheduledQueryService().run_recent_scrape(query_id)


@with_app_context
def sync_active_queries() -> None:
    """Periodic reconciliation: ensure every active query is scheduled."""
    from app.queue.scheduling import reconcile_query_schedules

    logger.info("SYNC_ACTIVE_QUERIES")
    reconcile_query_schedules()
