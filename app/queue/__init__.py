"""RQ-based background work: queues, jobs, scheduler loop, worker entry."""

from app.queue.connection import get_redis
from app.queue.queues import (
    QUEUE_DEFAULT,
    QUEUE_NOTIFY,
    QUEUE_SCRAPE,
    enqueue,
    get_queue,
)
from app.queue.scheduling import (
    enqueue_full_scrape,
    enqueue_recent_scrape,
    schedule_query_jobs,
    unschedule_query_jobs,
)

__all__ = [
    "get_redis",
    "QUEUE_DEFAULT",
    "QUEUE_NOTIFY",
    "QUEUE_SCRAPE",
    "enqueue",
    "get_queue",
    "enqueue_full_scrape",
    "enqueue_recent_scrape",
    "schedule_query_jobs",
    "unschedule_query_jobs",
]
