"""rq-scheduler entry point.

Owns two responsibilities:
  1. Bootstraps the periodic 'sync_active_queries' job (runs every 60s).
  2. Runs the rq-scheduler tick loop, enqueuing due jobs onto Redis.

Run as its own container so per-query schedules + the reconcile loop survive
API/worker restarts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from rq_scheduler import Scheduler

from app.queue.connection import get_redis
from app.queue.jobs import sync_active_queries
from app.queue.queues import QUEUE_DEFAULT
from app.queue.runtime import get_worker_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

SYNC_JOB_ID = "sync_active_queries"
SYNC_INTERVAL_SECONDS = 60


def _ensure_sync_job(sch: Scheduler) -> None:
    if SYNC_JOB_ID in sch:
        return
    sch.schedule(
        scheduled_time=datetime.utcnow() + timedelta(seconds=5),
        func=sync_active_queries,
        id=SYNC_JOB_ID,
        interval=SYNC_INTERVAL_SECONDS,
        repeat=None,
        queue_name=QUEUE_DEFAULT,
    )
    logger.info("Registered periodic %s every %ds", SYNC_JOB_ID, SYNC_INTERVAL_SECONDS)


def main() -> None:
    get_worker_app()
    sch = Scheduler(queue_name=QUEUE_DEFAULT, connection=get_redis())
    _ensure_sync_job(sch)
    logger.info("Starting rq-scheduler loop")
    sch.run()


if __name__ == "__main__":
    main()
