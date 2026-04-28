from types import SimpleNamespace
from datetime import datetime, timezone

import pytest

from app._scheduler.sync import ScheduledJobSynchronizer, query_id_from_job_id
from app.jobs import query_check
from app.searches.scheduled import ScheduledQueryService


def test_query_check_keeps_public_scheduled_callables():
    assert callable(query_check.full_scrape_job)
    assert callable(query_check.recent_scrape_job)
    assert callable(query_check.process_items)


def test_query_id_from_job_id_extracts_query_id():
    assert query_id_from_job_id("query_abc-123_full") == "abc-123"
    assert query_id_from_job_id("query_part_one_recent") == "part_one"


def test_query_id_from_job_id_ignores_non_query_jobs():
    assert query_id_from_job_id("sync_jobs") is None
    assert query_id_from_job_id("query_") is None


def test_scheduled_job_synchronizer_adds_missing_and_removes_stale_jobs():
    added = []
    removed = []
    scheduler = SimpleNamespace(
        get_jobs=lambda: [
            SimpleNamespace(id="query_active-b_recent"),
            SimpleNamespace(id="query_stale-c_full"),
            SimpleNamespace(id="sync_jobs"),
        ]
    )

    ScheduledJobSynchronizer(
        active_query_ids=lambda: ["active-a", "active-b"],
        scheduler_client=scheduler,
        add_jobs=added.append,
        remove_jobs=removed.append,
    ).sync()

    assert added == ["active-a"]
    assert removed == ["stale-c"]


def test_scheduled_query_service_runs_full_scrape_and_records_success():
    query = _query()
    session = _session()
    recorder = _run_recorder()
    processed = []
    now = datetime(2026, 4, 28, tzinfo=timezone.utc)

    ScheduledQueryService(
        query_repository=_query_repository(query),
        full_search=lambda *args, **kwargs: [{"ebay_id": "item-1"}],
        item_processor=lambda *args, **kwargs: processed.append((args, kwargs)),
        run_recorder=recorder,
        session=session,
        clock=lambda: now,
    ).run_full_scrape("query-1")

    assert processed
    assert query.first_run is False
    assert query.last_full_run == now
    assert recorder.started == [("query-1", "full")]
    assert recorder.succeeded == [("run-full", 1)]
    assert session.commits == 1


def test_scheduled_query_service_records_failed_run_before_reraising():
    query = _query()
    session = _session()
    recorder = _run_recorder()

    service = ScheduledQueryService(
        query_repository=_query_repository(query),
        full_search=_failing_search,
        run_recorder=recorder,
        session=session,
    )

    with pytest.raises(RuntimeError):
        service.run_full_scrape("query-1")

    assert recorder.failed == [("run-full", "search failed")]
    assert session.rollbacks == 1
    assert session.commits == 1


def _query():
    return SimpleNamespace(
        query_id="query-1",
        keyword_id="keyword-1",
        min_price=None,
        max_price=None,
        item_location="GB",
        condition=None,
        buying_options=None,
        required_keywords=None,
        excluded_keywords=None,
        marketplace="EBAY_GB",
        first_run=True,
        last_full_run=None,
        next_full_run=None,
        last_recent_run=None,
    )


def _query_repository(query):
    return SimpleNamespace(
        get_active=lambda query_id: query if query_id == query.query_id else None,
        get_keyword=lambda keyword_id: SimpleNamespace(keyword_text="camera"),
    )


def _session():
    class Session:
        def __init__(self):
            self.commits = 0
            self.rollbacks = 0

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

    return Session()


def _run_recorder():
    recorder = SimpleNamespace(started=[], succeeded=[], failed=[])

    def start(query, run_type):
        recorder.started.append((query.query_id, run_type))
        return f"run-{run_type}"

    def finish_success(run, item_count):
        recorder.succeeded.append((run, item_count))

    def finish_failure(run, error):
        recorder.failed.append((run, error))

    recorder.start = start
    recorder.finish_success = finish_success
    recorder.finish_failure = finish_failure
    return recorder


def _failing_search(*args, **kwargs):
    raise RuntimeError("search failed")
