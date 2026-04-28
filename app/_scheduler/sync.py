from collections.abc import Callable, Iterable
from typing import Protocol

from app._scheduler.job_manager import add_query_jobs, remove_query_jobs
from app.extensions import scheduler
from app.models import UserQuery

QUERY_JOB_PREFIX = "query_"


class SchedulerLike(Protocol):
    def get_jobs(self):
        """Return scheduled jobs."""


class ScheduledJobSynchronizer:
    """Reconcile active saved searches with APScheduler query jobs."""

    def __init__(
        self,
        active_query_ids: Callable[[], Iterable[str]] | None = None,
        scheduler_client: SchedulerLike | None = None,
        add_jobs: Callable[[str], None] = add_query_jobs,
        remove_jobs: Callable[[str], None] = remove_query_jobs,
    ) -> None:
        self.active_query_ids = active_query_ids or list_active_saved_search_ids
        self.scheduler = scheduler_client or scheduler
        self.add_jobs = add_jobs
        self.remove_jobs = remove_jobs

    def sync(self) -> None:
        active_query_ids = set(self.active_query_ids())
        scheduled_query_ids = self._scheduled_query_ids()

        print(f"SYNC_JOBS: Active queries: {len(active_query_ids)}")
        print(f"SYNC_JOBS: Scheduled queries: {len(scheduled_query_ids)}")

        self._add_missing_jobs(active_query_ids, scheduled_query_ids)
        self._remove_stale_jobs(active_query_ids, scheduled_query_ids)

    def _scheduled_query_ids(self) -> set[str]:
        scheduled_ids = set()
        for job in self.scheduler.get_jobs():
            query_id = query_id_from_job_id(job.id)
            if query_id:
                scheduled_ids.add(query_id)
        return scheduled_ids

    def _add_missing_jobs(
        self, active_query_ids: set[str], scheduled_query_ids: set[str]
    ) -> None:
        for query_id in active_query_ids - scheduled_query_ids:
            print(f"SYNC_JOBS: Adding job for query {query_id}")
            self.add_jobs(query_id)

    def _remove_stale_jobs(
        self, active_query_ids: set[str], scheduled_query_ids: set[str]
    ) -> None:
        for query_id in scheduled_query_ids - active_query_ids:
            print(f"SYNC_JOBS: Removing job for query {query_id}")
            self.remove_jobs(query_id)


def query_id_from_job_id(job_id: str) -> str | None:
    if not job_id.startswith(QUERY_JOB_PREFIX):
        return None

    parts = job_id.split("_")
    if len(parts) < 3:
        return None

    return "_".join(parts[1:-1])


def list_active_saved_search_ids() -> list[str]:
    rows = (
        UserQuery.query.with_entities(UserQuery.query_id)
        .filter_by(is_active=True)
        .all()
    )
    return [str(query_id) for (query_id,) in rows]
