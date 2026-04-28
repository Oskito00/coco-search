"""Named RQ queues + thin enqueue helpers."""

from __future__ import annotations

from rq import Queue

from app.queue.connection import get_redis

QUEUE_DEFAULT = "default"
QUEUE_SCRAPE = "scrape"
QUEUE_NOTIFY = "notify"

ALL_QUEUES = (QUEUE_DEFAULT, QUEUE_SCRAPE, QUEUE_NOTIFY)


def get_queue(name: str = QUEUE_DEFAULT) -> Queue:
    return Queue(name, connection=get_redis())


def enqueue(name: str, func, *args, **kwargs):
    return get_queue(name).enqueue(func, *args, **kwargs)
