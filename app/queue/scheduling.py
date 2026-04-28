"""Per-query scheduling: full + recent scrape cadence via rq-scheduler."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from rq_scheduler import Scheduler

from app.models import UserQuery
from app.queue.connection import get_redis
from app.queue.jobs import full_scrape, recent_scrape
from app.queue.queues import QUEUE_SCRAPE, enqueue

logger = logging.getLogger(__name__)

FULL_SCRAPE_INTERVAL_SECONDS = 24 * 60 * 60  # 24h
JOB_PREFIX = "query"


def _scheduler() -> Scheduler:
    return Scheduler(queue_name=QUEUE_SCRAPE, connection=get_redis())


def _full_id(query_id: str) -> str:
    return f"{JOB_PREFIX}:{query_id}:full"


def _recent_id(query_id: str) -> str:
    return f"{JOB_PREFIX}:{query_id}:recent"


def enqueue_full_scrape(query_id: str):
    return enqueue(QUEUE_SCRAPE, full_scrape, query_id)


def enqueue_recent_scrape(query_id: str):
    return enqueue(QUEUE_SCRAPE, recent_scrape, query_id)


def schedule_query_jobs(query_id: str, check_interval_minutes: int) -> None:
    """Idempotent: registers full + recent recurring jobs for a query."""
    sch = _scheduler()
    _cancel_if_present(sch, _full_id(query_id))
    _cancel_if_present(sch, _recent_id(query_id))

    sch.schedule(
        scheduled_time=datetime.utcnow(),
        func=full_scrape,
        args=[query_id],
        id=_full_id(query_id),
        interval=FULL_SCRAPE_INTERVAL_SECONDS,
        repeat=None,
        queue_name=QUEUE_SCRAPE,
    )
    sch.schedule(
        scheduled_time=datetime.utcnow() + timedelta(minutes=check_interval_minutes),
        func=recent_scrape,
        args=[query_id],
        id=_recent_id(query_id),
        interval=check_interval_minutes * 60,
        repeat=None,
        queue_name=QUEUE_SCRAPE,
    )
    logger.info("Scheduled query %s (interval=%dm)", query_id, check_interval_minutes)


def unschedule_query_jobs(query_id: str) -> None:
    sch = _scheduler()
    _cancel_if_present(sch, _full_id(query_id))
    _cancel_if_present(sch, _recent_id(query_id))
    logger.info("Unscheduled query %s", query_id)


def reconcile_query_schedules() -> None:
    """Add jobs for any active query missing one; remove jobs for inactive/deleted ones."""
    active = _active_query_map()
    scheduled = _scheduled_query_ids()

    for query_id in set(active.keys()) - scheduled:
        schedule_query_jobs(query_id, active[query_id])

    for query_id in scheduled - set(active.keys()):
        unschedule_query_jobs(query_id)


def _active_query_map() -> dict[str, int]:
    rows = (
        UserQuery.query.with_entities(UserQuery.query_id, UserQuery.check_interval)
        .filter_by(is_active=True)
        .all()
    )
    return {str(query_id): interval or 5 for query_id, interval in rows}


def _scheduled_query_ids() -> set[str]:
    sch = _scheduler()
    ids = set()
    for job in sch.get_jobs():
        parts = (job.id or "").split(":")
        if len(parts) == 3 and parts[0] == JOB_PREFIX:
            ids.add(parts[1])
    return ids


def _cancel_if_present(sch: Scheduler, job_id: str) -> None:
    try:
        sch.cancel(job_id)
    except Exception:
        pass
