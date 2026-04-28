"""CLI entry point for an RQ worker.

Usage (Docker):
    python -m app.queue.worker default
    python -m app.queue.worker scrape notify
"""

from __future__ import annotations

import logging
import sys

from rq import Worker

from app.queue.connection import get_redis
from app.queue.queues import ALL_QUEUES, get_queue
from app.queue.runtime import get_worker_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def main(argv: list[str]) -> None:
    queue_names = argv[1:] or list(ALL_QUEUES)
    _validate(queue_names)

    get_worker_app()  # eager-init Flask app + DB engine for the process
    queues = [get_queue(name) for name in queue_names]
    Worker(queues, connection=get_redis()).work()


def _validate(names: list[str]) -> None:
    unknown = [n for n in names if n not in ALL_QUEUES]
    if unknown:
        raise SystemExit(f"Unknown queues: {unknown}. Valid: {list(ALL_QUEUES)}")


if __name__ == "__main__":
    main(sys.argv)
